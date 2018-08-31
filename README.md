# Download attachments from Zendesk tickets

Zdgrab is a utility for downloading attachments to tickets from
[Zendesk](http://www.zendesk.com) and extracting and arranging them. There is
integration with [SendSafelyGrab](https://github.com/fprimex/SendSafelyGrab)
for downloading SendSafely package links included in comments.

## Installing

Tested with Python 2.7 and 3.7. Zdgrab requires
[zdeskcfg](http://github.com/fprimex/zdeskcfg) and
[zdesk](http://github.com/fprimex/zdesk) Python modules, which have their own
requirements.

```
pip install zdgrab
```

## Zendesk Authentication

Use one of the [authentication
mechanisms](https://github.com/fprimex/zdesk#authentication) supported by
`zdesk`. Configure `zdgrab` in `~/.zdeskcfg` similar to the following:

    # ~/.zdeskcfg
    [zdesk]
    url = https://example.zendesk.com
    email = util_account@example.com
    oauth = dneib393fwEF3ifbsEXAMPLEdhb93dw343
    # or
    # api = nde3ibb93fEwwwFXEAPMLEdb93d3www43

    [zdgrab]
    agent = you@example.com

### Usage

The script can be invoked with the following synopsis:

    usage: zdgrab [-h] [-v] [-t TICKETS] [-w WORK_DIR] [-a AGENT]
                  [--ss-host SS_HOST] [--ss-id SS_ID] [--ss-secret SS_SECRET]
                  [--ss-command SS_CMD] [--zdesk-email EMAIL]
                  [--zdesk-oauth OAUTH] [--zdesk-api API] [--zdesk-password PW]
                  [--zdesk-url URL] [--zdesk-token]

    Download attachments from Zendesk tickets.

    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose         verbose output
      -t TICKETS, --tickets TICKETS
                            Ticket(s) to grab attachments (default: all of your
                            open tickets)
      -w WORK_DIR, --work-dir WORK_DIR
                            Working directory in which to store attachments.
                            (default: ~/zdgrab/)
      -a AGENT, --agent AGENT
                            Agent whose open tickets to search (default: me)
      --ss-host SS_HOST     SendSafely host to connect to, including protocol
      --ss-id SS_ID         SendSafely API key
      --ss-secret SS_SECRET
                            SendSafely API secret
      --ss-command SS_CMD   SendSafely command
      --zdesk-email EMAIL   zendesk login email
      --zdesk-oauth OAUTH   zendesk OAuth token
      --zdesk-api API       zendesk API token
      --zdesk-password PW   zendesk password or token
      --zdesk-url URL       zendesk instance URL
      --zdesk-token         specify if password is a zendesk token (deprecated)

Note that command line arguments such as `-agent` and `-work_dir` can also be
specified (in lowercase form) within the appropriate section of `.zdeskcfg` as
well as, e.g., `agent` and `work_dir`.

Here are some basic zdgrab usage examples to get started:

### SendSafely support

Zdgrab supports downloading [SendSafely](https://www.sendsafely.com/) packages
with [SendSafelyGrab](https://github.com/fprimex/SendSafelyGrab). To set this
up, obtain API credentials from SendSafely for the account to be used. Set the
credentials and other configuration items in `~/.zdeskcfg` or provide them as
command line parameters: `ss_host`, `ss_id`, `ss_secret`, `ss_command`.

The `SendSafelyGrab.exe` command is a C# .NET program. It supports running on
Windows with .NET and also on other platforms using `mono`. Download the
`SendSafelyGrab` release and extract it somewhere onto the filesystem. Set
`ss_command` to the full path to `SendSafelyGrab.exe`. If using `mono`, set the
command to, e.g., `mono /path/to/SendSafelyGrab.exe`. If using `~/.zdeskcfg`,
the path should, unfortunately, not contain spaces.

With `ss_command` set, `zdgrab` will search all ticket comments for SendSafely
links to packages (for example, those added by the SendSafely Zendesk app).
When it finds a link, it will run `SendSafelyGrab.exe` with the arguments
necessary to retrieve the packaged files. As with attachments, the files will
be extracted automatically.

#### Help

    zdgrab -h

#### Get/update all attachment for your open tickets

    zdgrab

#### Get/update all attachments for your open tickets with verbose output

    zdgrab -v

#### Get/update all attachments from a specific ticket

    zdgrab -t 2940

#### Get/update all attachments from a number of specific tickets

    zdgrab -t 2940,3405,3418

## Notes

zdgrab uses Zendesk API version 2 with JSON

zdgrab depends on the following Python modules:

* `zdesk`
  - `requests`
* `zdeskcfg`
  - `plac_ini`
  - `plac`

### Resources

* Python zdesk module: https://github.com/fprimex/zdesk
* Python zdeskcfg module: https://github.com/fprimex/zdeskcfg
* Zendesk Developer Site (For API information): http://developer.zendesk.com

### Using zdgrab as a module

It can be useful to script zdgrab using Python. The configuration is performed
followed by the zdgrab, then the return value of the zdgrab can then be used to
operate on the attachments and directories that were grabbed. For example:

```
#!/usr/bin/env python

from __future__ import print_function

import os
import zdeskcfg
from zdgrab import zdgrab

if __name__ == '__main__':
    # Using zdeskcfg will cause this script to have all of the ini
    # and command line parsing capabilities of zdgrab.

    # Passing eager=False is required in this case, otherwise plac and plac_ini
    # will wrap the function value with list() and destroy the grabs dict.

    grabs = zdeskcfg.call(zdgrab, section='zdgrab', eager=False)

    start_dir = os.path.abspath(os.getcwd())

    for ticket_dir in grabs.keys():
        attach_path = grabs[ticket_dir]
        # Path to the ticket dir containing the attachment
        # os.chdir(ticket_dir)

        # Path to the attachment that was grabbed
        # os.path.join(ticket_dir, attach_path)

        # Path to the comments dir in this ticket dir
        ticket_com_dir = os.path.join(ticket_dir, 'comments')

        # Handy way to get a list of the comment dirs in numerical order:
        comment_dirs = [dir for dir in os.listdir(ticket_com_dir) if dir.isdigit()]
        comment_dirs = map(int, comment_dirs) # convert to ints
        comment_dirs = map(str, sorted(comment_dirs)) # sort and convert back to strings

        # Iterate through the dirs and over every file
        os.chdir(ticket_com_dir)
        for comment_dir in comment_dirs:
            for dirpath, dirnames, filenames in os.walk(comment_dir):
                for filename in filenames:
                    print(os.path.join(ticket_com_dir, dirpath, filename))

    os.chdir(start_dir)
```

### Zdsplode

Archives that are downloaded are automatically extracted using an included
function called `zdsplode`. A command line script for calling zdsplode is also
included.

