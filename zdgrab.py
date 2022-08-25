"""
zdgrab: Download attachments from Zendesk tickets
"""

import os
import sys
import re
import textwrap
import base64
import json

from datetime import datetime, timedelta
from zdesk.zdesk import get_id_from_url

import zdeskcfg
from zdesk import Zendesk

from asplode import asplode


try:
    from ssgrab import ssgrab
    ss_present = True
except ModuleNotFoundError:
    ss_present = False


class verbose_printer:
    def __init__(self, v):
        if v:
            self.print = self.verbose_print
        else:
            self.print = self.null_print

    def verbose_print(self, msg, end='\n'):
        print(msg, file=sys.stderr, end=end)

    def null_print(self, msg, end='\n'):
        pass


@zdeskcfg.configure(
    verbose=('verbose output',
                 'flag', 'v'),
    tickets=('Comma separated ticket numbers to grab (default: all of your open tickets)',
                 'option', 't', str, None, 'TICKETS'),
    orgs=('Grab from one or more Organizations (default: none)',
                 'option', 'o', str, None, 'ORGS'),
    items=('Comma separated items to grab: attachments,comments,audits (default: attachments)',
                 'option', 'i', str, None, 'ITEMS'),
    status=('Query expression for ticket status (default: <solved)',
                 'option', 's', str, None, 'STATUS'),
    query=('Additional query when searching tickets (default: "")',
                 'option', 'q', str, None, 'QUERY'),
    days=('Retrieve tickets opened since a number of days (default: 0, all)',
                 'option', 'd', int, None, 'DATETIME'),
    js=('Save response information in JSON format (default: false)',
                 'flag', 'j'),
    count=('Retrieve up to this many total specified items (default: 0, all)',
                 'option', 'c', int, None, 'COUNT'),
    work_dir=('Working directory to store items in (default: ~/zdgrab)',
                 'option', 'w', str, None, 'WORK_DIR'),
    agent=('Agent whose open tickets to search (default: me)',
                 'option', 'a', str, None, 'AGENT'),
    ss_host=('SendSafely host to connect to, including protocol',
                 'option', None, str, None, 'SS_HOST'),
    ss_id=('SendSafely API key',
                 'option', None, str, None, 'SS_ID'),
    ss_secret=('SendSafely API secret',
                 'option', None, str, None, 'SS_SECRET'),
)
def _zdgrab(verbose=False,
            tickets=None,
            orgs=None,
            items="attachments",
            status="<solved",
            query="",
            days=0,
            js=False,
            count=0,
            work_dir=os.path.join(os.path.expanduser('~'), 'zdgrab'),
            agent='me',
            ss_host=None,
            ss_id=None,
            ss_secret=None):
    "Download attachments from Zendesk tickets."

    cfg = _zdgrab.getconfig()

    zdgrab(verbose=verbose,
           tickets=tickets,
           orgs=orgs,
           items=items,
           status=status,
           query=query,
           days=days,
           js=js,
           count=count,
           work_dir=work_dir,
           agent=agent,
           ss_host=ss_host,
           ss_id=ss_id,
           ss_secret=ss_secret,
           zdesk_cfg=cfg)


def zdgrab(verbose, tickets, orgs, status, query, items, days, js, count,
           work_dir, agent, ss_host, ss_id, ss_secret, zdesk_cfg):
    # ssgrab will only be invoked if the comment body contains a link.
    # See the corresponding REGEX used by them, which has been ported to Python:
    # https://github.com/SendSafely/Windows-Client-API/blob/master/SendsafelyAPI/Utilities/ParseLinksUtility.cs
    ss_link_re = r'https://[-a-zA-Z\.]+/receive/\?[-A-Za-z0-9&=]+packageCode=[-A-Za-z0-9_]+#keyCode=[-A-Za-z0-9_]+'
    ss_link_pat = re.compile(ss_link_re)

    vp = verbose_printer(verbose)

    if zdesk_cfg.get('zdesk_url') and (
            zdesk_cfg.get('zdesk_oauth') or
            (zdesk_cfg.get('zdesk_email') and zdesk_cfg.get('zdesk_password')) or
            (zdesk_cfg.get('zdesk_email') and zdesk_cfg.get('zdesk_api'))
    ):
        vp.print(f'Configuring Zendesk with:\n'
                 f'  url: {zdesk_cfg.get("zdesk_url")}\n'
                 f'  email: {zdesk_cfg.get("zdesk_email")}\n'
                 f'  token: {repr(zdesk_cfg.get("zdesk_token"))}\n'
                 f'  password/oauth/api: (hidden)\n')

        zd = Zendesk(**zdesk_cfg)
    else:
        msg = textwrap.dedent("""\
            Error: Need Zendesk config to continue.

            Config file (~/.zdeskcfg) should be something like:
            [zdesk]
            url = https://example.zendesk.com
            email = you@example.com
            api = dneib393fwEF3ifbsEXAMPLEdhb93dw343
            # or
            # oauth = ndei393bEwF3ifbEsssX

            [zdgrab]
            agent = agent@example.com
            """)
        print(msg)
        return 1

    # Log the cfg
    vp.print(f'Running with zdgrab config:\n'
             f' verbose:  {verbose}\n'
             f' tickets:  {tickets}\n'
             f' orgs:     {orgs}\n'
             f' items:    {items}\n'
             f' status:   {status}\n'
             f' query:    {query}\n'
             f' days:     {days}\n'
             f' js:       {js}\n'
             f' count:    {count}\n'
             f' work_dir: {work_dir}\n'
             f' agent:    {agent}\n')

    if not items:
        print('Error: No items given to grab')
        return 1

    if days > 0:
        start_time = datetime.utcnow() - timedelta(days=days)
    else:
        # UNIX epoch, 1969
        start_time = datetime.fromtimestamp(0)

    possible_items = {"attachments", "comments", "audits"}
    items = set(items.split(','))

    grab_items = possible_items.intersection(items)
    invalid_items = items - possible_items

    if len(invalid_items) > 0:
        print(f'Error: Invalid item(s) specified: {invalid_items} ')
        return 1

    # tickets=None means default to getting all of the attachments for this
    # user's open tickets. If tickets is given, try to split it into ints
    if tickets:
        # User gave a list of tickets
        try:
            tickets = [int(i) for i in tickets.split(',')]
        except ValueError:
            print(f'Error: Could not convert to integers: {tickets}')
            return 1

    # dict of paths to attachments retrieved to return. format is:
    # { 'path/to/ticket/1': [ 'path/to/attachment1', 'path/to/attachment2' ],
    #   'path/to/ticket/2': [ 'path/to/attachment1', 'path/to/attachment2' ] }
    grabs = {}

    # list to hold all of the ticket objects retrieved
    results = []

    # list to hold all of the ticket numbers being retrieved
    ticket_nums = []

    if orgs:
        orgs = orgs.split(',')
        for o in orgs:
            resp = zd.search(query=f'type:organization "{o}"')

            if resp["count"] == 0:
                print(f'Error: Could not find org {o}')
                continue
            elif resp["count"] > 1:
                print(f'Error: multiple results for org {o}')
                for result in resp["results"]:
                    print(f'  {result["name"]}')
                continue

            q = f'type:ticket organization:"{o}" status{status} created>{start_time.isoformat()[:10]} {query}'
            resp = zd.search(query=q, get_all_pages=True)
            results.extend(resp['results'])

    # Save the current directory so we can go back once done
    start_dir = os.getcwd()

    # Normalize all of the given paths to absolute paths
    work_dir = os.path.abspath(work_dir)

    # Check for and create working directory
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir)

    # Change to working directory to begin file output
    os.chdir(work_dir)

    vp.print('Retrieving tickets')

    if tickets:
        # tickets given, query for those. tickets that are explicitly requested
        # are retrieved regardless as to other options such as since.
        response = zd.tickets_show_many(ids=','.join([s for s in map(str, tickets)]),
                                        get_all_pages=True)

        # tickets_show_many is not a search, so manually insert 'result_type'
        for t in response['tickets']:
            t['result_type'] = 'ticket'

        results.extend(response['tickets'])

    if not tickets and not orgs:
        # No ticket or org given. Get all of the attachments for all of this
        # user's tickets.
        q = f'status{status} assignee:{agent} created>{start_time.isoformat()[:10]} {query}'
        response = zd.search(query=q, get_all_pages=True)
        results.extend(response['results'])

        if response['count'] == 0:
            # No tickets from which to get attachments
            print("No tickets found for retrieval.")
            return {}

    vp.print(f'Located {len(results)} tickets')

    # Fix up some headers to use for downloading the attachments.
    # We're going to borrow the zdesk object's httplib client.
    headers = {}
    if zd.zdesk_email is not None and zd.zdesk_password is not None:
        basic = base64.b64encode(zd.zdesk_email.encode('ascii') +
                                 b':' + zd.zdesk_password.encode('ascii'))
        headers["Authorization"] = f"Basic {basic}"

    for i, ticket in enumerate(results):
        if ticket['result_type'] != 'ticket':
            del results[i]

        ticket_nums.append(ticket['id'])

    # Get the items from the given zendesk tickets
    for i, ticket in enumerate(results):
        vp.print(f'Ticket {ticket["id"]}')

        ticket_dir = os.path.join(work_dir, str(ticket['id']))
        ticket_com_dir = os.path.join(ticket_dir, 'comments')
        comment_num = 0
        attach_num = 0

        if not os.path.isdir(ticket_dir):
            os.makedirs(ticket_dir)

        if js:
            os.chdir(ticket_dir)
            with open('ticket.json', 'w') as f:
                json.dump(ticket, f, indent=2)

        response = zd.ticket_audits(ticket_id=ticket['id'],
                                    get_all_pages=True)

        audits = response['audits'][::-1]
        audit_num = len(audits) + 1
        results[i]['audits'] = audits

        for audit in audits:
            audit_time = audit.get('created_at')
            audit_num -= 1
            for event in audit['events']:
                comment_num = audit_num
                comment_dir = os.path.join(ticket_com_dir, str(comment_num))

                if js:
                    if not os.path.isdir(comment_dir):
                        os.makedirs(comment_dir)

                    os.chdir(comment_dir)
                    with open('comment.json', 'w') as f:
                        json.dump(event, f, indent=2)

                if event['type'] == 'Comment' and 'comments' in grab_items:
                    comment_time = event.get('created_at', audit_time)
                    if not comment_time:
                        comment_time = 'unknown time'

                    if os.path.isfile(os.path.join(comment_dir, 'comment.txt')):
                        vp.print(f' Comment {comment_num} already present')
                    else:
                        # Check for and create the download directory
                        if not os.path.isdir(comment_dir):
                            os.makedirs(comment_dir)

                        os.chdir(comment_dir)
                        with open('comment.txt', 'w') as f:
                            if event['public']:
                                visibility = 'Public'
                            else:
                                visibility = 'Private'

                            vp.print(f' Writing comment {comment_num}')
                            f.write(f'{visibility} comment by {event["author_id"]} at {comment_time}')
                            f.write(event['body'])

                if count > 0 and attach_num >= count:
                    break

                if 'attachments' not in grab_items or event['type'] != 'Comment':
                    continue

                for attachment in event['attachments']:
                    attach_num += 1

                    if count > 0:
                        attach_msg = f' ({attach_num}/{count})'
                    else:
                        attach_msg = f' ({attach_num})'

                    name = attachment['file_name']
                    if os.path.isfile(os.path.join(comment_dir, name)):
                        vp.print(
                            f' Attachment {name} already present{attach_msg}')
                        continue

                    # Get this attachment
                    vp.print(f' Downloading attachment {name}{attach_msg}')

                    # Check for and create the download directory
                    if not os.path.isdir(comment_dir):
                        os.makedirs(comment_dir)

                    os.chdir(comment_dir)
                    response = zd.client.request('GET',
                                                 attachment['content_url'],
                                                 headers=headers)

                    if response.status_code != 200:
                        print(f'Error downloading {attachment["content_url"]}')
                        continue

                    with open(name, 'wb') as f:
                        f.write(response.content)

                    # Check for and create the grabs entry to return
                    if ticket_dir not in grabs:
                        grabs[ticket_dir] = []

                    grabs[ticket_dir].append(
                        os.path.join('comments', str(comment_num), name))

                    # Let's try to extract this if it's compressed
                    asplode(name, verbose=verbose)

                if not ss_present:
                    continue

                for link in ss_link_pat.findall(event['body']):
                    attach_num += 1

                    if count > 0:
                        attach_msg = f' ({attach_num}/{count})'
                    else:
                        attach_msg = f' ({attach_num})'

                    ss_files = ssgrab(verbose=verbose, key=ss_id, secret=ss_secret,
                                      host=ss_host, link=link, work_dir=comment_dir,
                                      postmsg=attach_msg)

                    # Check for and create the grabs entry to return
                    if ss_files and (ticket_dir not in grabs):
                        grabs[ticket_dir] = []

                    for name in ss_files:
                        grabs[ticket_dir].append(
                            os.path.join('comments', str(comment_num), name))

                        # Let's try to extract this if it's compressed
                        os.chdir(comment_dir)
                        asplode(name, verbose=verbose)

    if js:
        os.chdir(work_dir)
        with open('tickets.js', "a+") as f:
            tickets_data = f.read()

            if tickets_data:
                ticketsjs = json.loads(tickets_data)

                if ticketsjs:
                    for i, ticket in enumerate(ticketsjs):
                        if ticket['id'] in ticket_nums:
                            del ticketsjs[i]

                    results.extend(ticketsjs)

            f.seek(0)
            f.write(json.dumps(results, indent=2))
            f.truncate()

    os.chdir(start_dir)
    return grabs


def main(argv=None):
    zdeskcfg.call(_zdgrab, section='zdgrab')
