"""
zdgrab: Download attachments from Zendesk tickets
"""

from __future__ import print_function

import os
import sys
import textwrap
import base64

import zdeskcfg
from zdesk import Zendesk

from .zdsplode import zdsplode

@zdeskcfg.configure(
    verbose=('verbose output', 'flag', 'v'),
    tickets=('Ticket(s) to grab attachments (default: all of your open tickets)',
                      'option', 't', None, None, 'TICKETS'),
    work_dir=('Working directory in which to store attachments. (default: ~/zdgrab/)',
                      'option', 'w', None, None, 'WORK_DIR'),
    agent=('Agent whose open tickets to search (default: me)',
                      'option', 'a', None, None, 'AGENT'),
    )
def zdgrab(verbose=False,
           tickets=None,
           work_dir=os.path.join(os.path.expanduser('~'), 'zdgrab'),
           agent='me'):
    "Download attachments from Zendesk tickets."

    cfg = zdgrab.getconfig()

    if cfg['zdesk_url'] and cfg['zdesk_email'] and cfg['zdesk_password']:
        if verbose:
            print('Configuring Zendesk with:\n'
                  '  url: {}\n'
                  '  email: {}\n'
                  '  token: {}\n'
                  '  password: (hidden)\n'.format( cfg['zdesk_url'],
                                                   cfg['zdesk_email'],
                                                   repr(cfg['zdesk_token']) ))
        zd = Zendesk(**cfg)
    else:
        msg = textwrap.dedent("""\
            Error: Need Zendesk config to continue.

            Config file (~/.zdeskcfg) should be something like:
            [zdesk]
            url = https://example.zendesk.com
            email = you@example.com
            password = dneib393fwEF3ifbsEXAMPLEdhb93dw343
            token = 1

            [zdgrab]
            agent = agent@example.com
            """)
        print(msg)
        return 1

    # Log the cfg
    if verbose:
        print('Running with zdgrab config:\n'
              ' verbose: {}\n'
              ' tickets: {}\n'
              ' work_dir: {}\n'
              ' agent: {}\n'.format(verbose, tickets, work_dir, agent))

    # tickets=None means default to getting all of the attachments for this
    # user's open tickets. If tickets is given, try to split it into ints
    if tickets:
        # User gave a list of tickets
        try:
            tickets = [int(i) for i in tickets.split(',')]
        except ValueError:
            print('Error: Could not convert to integers: {}'.format(tickets))
            return 1

    # dict of paths to attachments retrieved to return. format is:
    # { 'path/to/ticket/1': [ 'path/to/attachment1', 'path/to/attachment2' ],
    #   'path/to/ticket/2': [ 'path/to/attachment1', 'path/to/attachment2' ] }
    grabs = {}

    # Save the current directory so we can go back once done
    start_dir = os.getcwd()

    # Normalize all of the given paths to absolute paths
    work_dir = os.path.abspath(work_dir)

    # Check for and create working directory
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir)

    # Change to working directory to begin file output
    os.chdir(work_dir)

    if verbose:
        print('Retrieving tickets')

    if tickets:
        # tickets given, query for those
        response = zd.tickets_show_many(ids=','.join([s for s in map(str,tickets)]),
                get_all_pages=True)
        result_field = 'tickets'
    else:
        # List of tickets not given. Get all of the attachments for all of this
        # user's open tickets.
        q = 'status<solved assignee:{}'.format(agent)
        response = zd.search(query=q, get_all_pages=True)
        result_field = 'results'

    if response['count'] == 0:
        # No tickets from which to get attachments
        print("No tickets provided for attachment retrieval.")
        return {}

    results = response[result_field]

    # Fix up some headers to use for downloading the attachments.
    # We're going to borrow the zdesk object's httplib client.
    headers = {}
    if zd.zdesk_email is not None and zd.zdesk_password is not None:
        headers["Authorization"] = "Basic {}".format(
            base64.b64encode(zd.zdesk_email.encode('ascii') + b':' +
                             zd.zdesk_password.encode('ascii')))

    # Get the attachments from the given zendesk tickets
    for ticket in results:
        if result_field == 'results' and ticket['result_type'] != 'ticket':
            # This is not actually a ticket. Weird. Skip it.
            continue

        if verbose:
            print('Ticket {}'.format(ticket['id']))

        ticket_dir = os.path.join(work_dir, str(ticket['id']))
        ticket_com_dir = os.path.join(ticket_dir, 'comments')
        comment_num = 0

        if verbose:
            print('Retrieving audits')

        response = zd.ticket_audits(ticket_id=ticket['id'],
                get_all_pages=True)
        audits = response['audits']

        for audit in audits:
            for event in audit['events']:
                if event['type'] != 'Comment':
                    # This event isn't a comment. Skip it.
                    continue

                comment_num += 1
                comment_dir = os.path.join(ticket_com_dir, str(comment_num))

                if verbose and event['attachments']:
                    print('Comment {}'.format(comment_num))

                for attachment in event['attachments']:
                    name = attachment['file_name']
                    if os.path.isfile(os.path.join(comment_dir, name)):
                        if verbose:
                            print('Attachment {} already present'.format(name))
                        continue

                    # Get this attachment
                    if verbose:
                        print('Attachment {}'.format(name))

                    # Check for and create the download directory
                    if not os.path.isdir(comment_dir):
                        os.makedirs(comment_dir)

                    os.chdir(comment_dir)
                    response, content = zd.client.request(attachment['content_url'], headers=headers)
                    if response['status'] != '200':
                        print('Error downloading {}'.format(attachment['content_url']))
                        continue

                    with open(name, 'wb') as f:
                        f.write(content)

                    # Check for and create the grabs entry to return
                    if ticket_dir not in grabs:
                        grabs[ticket_dir] = []

                    grabs[ticket_dir].append(
                        os.path.join('comments', str(comment_num), name) )

                    # Let's try to extract this if it's compressed
                    zdsplode(name, verbose=verbose)

    os.chdir(start_dir)
    return grabs


def main(argv=None):
    zdeskcfg.call(zdgrab, section='zdgrab')
    return 0

