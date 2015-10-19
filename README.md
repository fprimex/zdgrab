# Download attachments from Zendesk tickets

Zdgrab is a utility for downloading attachments to tickets from
[Zendesk](http://www.zendesk.com) and extracting and arranging them.

## Installing

Tested with Python 2.7 and 3.4. Zdgrab requires
[zdeskcfg](http://github.com/fprimex/zdeskcfg) and
[zdesk](http://github.com/fprimex/zdesk) Python modules, which have their own
requirements.

```
pip install zdgrab
```

You may wish to use easy\_install instead of pip, and use a virtualenv.

## Zendesk API Token Setup

Note: Users can use a Zendesk shared account and its access token. In this
shared account setup, set 'email' to the shared account, and set 'agent' to
your email address in the configuration file.

Prior to using zdgrab, a Zendesk API token must be generated for the account
that will be used. This token helps avoid disclosing the Zendesk user account
password, and it can be regenerated or disabled altogether at any time.

To create a Zendesk API token for use with zdgrab, follow these steps:

1. Log into your Zendesk website: https://example.zendesk.com
2. Navigate to the API settings: https://example.zendesk.com/settings/api/
3. Click the **Enabled** checkbox inside the **Token Access** section.
4. Make note of the 40 character string after *Your API token is:*
5. Click Save.

**NOTE**: If problems occur with step #3 above, the account used to access
Zendesk could lack the necessary permissions to work with an API token. In this
case, appropriate permissions should be requested from your administrator.

Once the Zendesk API token is configured, and noted, proceed to configuring
a Python virtual environment.

### Configuration

Options when running zdgrab can be configured through configuration files.  An
example of the config file is given below. If you have API access directly
using your account, then set `email` to your Zendesk account login. If your
organization uses a shared account for utilities, then set `email` to the
utilities account and set `agent` to your Zendesk login.

    # ~/.zdeskcfg
    [zdesk]
    email = util_account@example.com
    password = dneib393fwEF3ifbsEXAMPLEdhb93dw343
    url = https://example.zendesk.com
    token = 1

    [zdesk]
    agent = you@example.com

### Usage

The script can be invoked with the following synopsis:

    usage: zdgrab [-h] [-v] [-t TICKETS] [-w WORK_DIR] [-a AGENT]
                  [--zdesk-email EMAIL] [--zdesk-password PW] [--zdesk-url URL]
                  [--zdesk-token]

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
      --zdesk-email EMAIL   zendesk login email
      --zdesk-password PW   zendesk password or token
      --zdesk-url URL       zendesk instance URL
      --zdesk-token         specify if password is a zendesk token

Here are some basic zdgrab usage examples to get started:

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

* zdesk
  - requests
* zdeskcfg
  - plac\_ini
  - plac

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

