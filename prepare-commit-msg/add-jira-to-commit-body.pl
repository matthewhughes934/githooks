#!/usr/bin/env perl

use strict;
use warnings;

require 5.008;

=head1 prepare-commit-hook

Searches your branch for a ticket of the form C<< LABEL >>-1234> and if it exists,
adds the ticket to the body of your commit when C<git commit> is invoked with
source C<message> or C<commit> (see L<https://git-scm.com/docs/githooks>, or
L<githooks(5)> for details).

For example:

    $ git checkout -b FOO-1234/my-new-feature
    # make some changes...
    $ git commit --all --message "Add the new feature!"
    $ git log -1
    commit 2c49333eabcd2f92d39a341ebaf47bbdb2e5b275 (HEAD -> FOO-1234/my-new-feature)
    Author: John Smith <john.smith@email.com>
    Date:   Mon Dec 7 20:25:45 2020 -0500

        Add the new feature!
        
        Ticket: FOO-1234

=cut

# EDIT ME: List of JIRA labels to accept
my @JIRA_LABELS = qw(FOO BAR);

# EDIT ME: Prefix for the ticket in the body
my $TICKET_PREFIX = "Ticket: ";

#$ARGV[2] is the commit SHA, unused here
my $COMMIT_MSG_FILE = $ARGV[0];
my $COMMIT_SOURCE   = $ARGV[1];

# invoked with --message/-m or -F/--file
my $SOURCE_IS_MESSAGE = $COMMIT_SOURCE && $COMMIT_SOURCE eq 'message';

# invoked with -c/--reuse-message or -C/--reedit-message or --ammed
my $SOURCE_IS_COMMIT = $COMMIT_SOURCE && $COMMIT_SOURCE eq 'commit';
my $IS_SUPPORTED_SOURCE =
  !$COMMIT_SOURCE || $SOURCE_IS_MESSAGE || $SOURCE_IS_COMMIT;

sub get_ticket_from_branch {
    my $branch = qx/git rev-parse --abbrev-ref HEAD/;
    chomp($branch);

    for my $label (@JIRA_LABELS) {
        if ( $branch =~ m/(\Q$label\E-[0-9]+)/ ) {
            return $1;
        }
    }
    return;
}

sub get_ticket_string {
    my ($ticket) = @_;

    return "$TICKET_PREFIX $ticket";
}

sub add_ticket_to_commit {
    my ($ticket) = @_;

    if ($IS_SUPPORTED_SOURCE) {
        my $content = read_file_contents($COMMIT_MSG_FILE);
        write_ticket_to_file( $COMMIT_MSG_FILE, $content, $ticket );
    }
    return;
}

sub write_ticket_to_file {
    my ( $filename, $content, $ticket ) = @_;

    my $ticket_string = get_ticket_string($ticket);

    # noop if ticket already in commit
    return if $content =~ /\Q$ticket_string\E/;

    my $out_content = q//;
    if ( !$COMMIT_SOURCE ) {
        $out_content = _content_for_new_commit( $content, $ticket_string );
    }
    elsif ($SOURCE_IS_MESSAGE) {
        $out_content = _content_for_message( $content, $ticket_string );
    }
    elsif ($SOURCE_IS_COMMIT) {
        $out_content =
          _content_for_exisiting_commit( $content, $ticket_string );
    }
    open( my $out, '>:encoding(utf8)', $filename )
      or die 'Could not open commit message file';
    print( $out $out_content );
    close($out) or warn 'Error closing commit file after write';
    return;
}

sub _content_for_new_commit {
    my ( $content, $ticket_string ) = @_;

    # Fresh commit, file contains some empty lines followed by the auto
    # generated comments, just insert our ticket before these comments
    return "\n\n" . $ticket_string . $content;
}

sub _content_for_message {
    my ( $content, $ticket_string ) = @_;

    # Commit file already contains the message, just insert the ticket after
    # this
    return $content . "\n\n" . $ticket_string;
}

sub _content_for_exisiting_commit {
    my ( $content, $ticket_string ) = @_;

    # Commit file already exists and holds a commit. We want to place the
    # ticket after the commit text, but before the auto generated comments
    return $content =~ s/(^#)/$ticket_string\n$1/mr;
}

sub read_file_contents {
    my ($filename) = @_;

    open( my $in, '<:encoding(utf8)', $COMMIT_MSG_FILE )
      or die 'Could not open commit message file';
    local $/ = undef;    # 'slurp mode'
    my $content = <$in>;
    close($in) or warn 'Error closing commit file after read';
    return $content;
}

my $branch_ticket = get_ticket_from_branch() or exit 0;
add_ticket_to_commit($branch_ticket);
