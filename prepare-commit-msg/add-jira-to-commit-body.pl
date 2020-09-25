#!/usr/bin/env perl

use strict;
use warnings;

=head1 prepare-commit-hook

Add "Ticket: <JIRA TICKET>" to the body of your commit before editing or when
C<git commit> is invoked with C<--message/-m>. Does nothing when the commit is
a C<merge> or C<template>. Expects the JIRA ticket to be of the form
"LABEL-1234".

=cut

my $COMMIT_MSG_FILE = $ARGV[0];
my $COMMIT_SOURCE   = $ARGV[1];

#my $SHA = $ARGV[2]; # unused

my @JIRA_LABELS    = qw(FOO BAR);  # List of JIRA labels to accept
my $MESSAGE_SOURCE = 'message';

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

    return "\n\nTicket: $ticket";
}

sub add_ticket_to_commit {
    my ($ticket) = @_;

    if ( !$COMMIT_SOURCE || $COMMIT_SOURCE eq $MESSAGE_SOURCE ) {
        my $content = read_file_contents($COMMIT_MSG_FILE);
        write_ticket_to_file( $COMMIT_MSG_FILE, $content, $ticket );
    }
}

sub write_ticket_to_file {
    my ( $filename, $content, $ticket ) = @_;

    my $ticket_string = get_ticket_string($ticket);
    open( my $out, '>:encoding(utf8)', $filename )
        or die 'Could not open commit message file';

    if ( !$COMMIT_SOURCE ) {
        print( $out $ticket_string );
        print( $out $content );
    }
    elsif ( $COMMIT_SOURCE eq $MESSAGE_SOURCE ) {
        print( $out $content );
        print( $out $ticket_string );
    }
    close($out);
}

sub read_file_contents {
    my ($filename) = @_;

    open( my $in, '<:encoding(utf8)', $COMMIT_MSG_FILE )
      or die 'Could not open commit message file';
    local $/ = undef;    # 'slurp mode'
    my $content = <$in>;
    close($in);
    return $content;
}

my $branch_ticket = get_ticket_from_branch() or exit 0;
add_ticket_to_commit( $branch_ticket );
