"""
This module contains definitions of various sendto functions:
functions that take a user, and return a list of associated sendto addresses.
These addresses are (email address, name) pairs.
"""

import re

def send_to_self(user):
    """
    Returns a single address, the user's own address.
    """
    try:
        return [user.get_email_sendto_address_pair()]
    except:
        return []

def _send_to_contact(contact):
    """
    Returns a sendto function that returns a single address, one of the user's
    contacts.  Can be either the guardian or the emergency contact, depending
    on whether contact is 'guardian' or 'emergency'.
    """
    def sendto_fn(user):
        """
        Returns a single address, the user's %s contact.
        Can also return no addresses, if the contact does not exist.
        """
        try:
            profile = user.getLastProfile()
            if profile:
                contact_info = getattr(profile, 'contact_' + contact, profile.contact_guardian)
                if contact_info and contact_info.email:
                    return [contact_info.get_email_sendto_address_pair()]
        except:
            pass
        return []
    sendto_fn.__doc__ = sendto_fn.__doc__ % contact
    sendto_fn.__name__ = 'send_to_' + contact
    return sendto_fn

send_to_guardian = _send_to_contact('guardian')

send_to_emergency = _send_to_contact('emergency')

def _send_to_combination(sendto_fns):
    """
    Given a list of sendto functions, returns a sendto function that returns
    the concatenation of all their outputs. Duplicate emails are ignored.
    """
    def sendto_fn(user):
        """
        Returns the concatenation of the outputs of the following sendto
        functions:
        """
        emails = []
        address_pairs = []
        for fn in sendto_fns:
            try:
                for address_pair in fn(user):
                    if address_pair[0] not in emails:
                        # Duplicate emails are ignored.
                        emails.append(address_pair[0])
                        address_pairs.append(address_pair)
            except:
                pass
        return address_pairs

    # Some docstring formatting
    sendto_fn.__doc__ = re.sub('^[ \t]*', '', sendto_fn.__doc__, flags=re.MULTILINE)

    # Append the name and docstring of each component function, with some formatting.
    for fn in sendto_fns:
        sendto_fn.__doc__ += "\n%s:\n%s" % (fn.__name__, re.sub('\n *', '\n    ', fn.__doc__).strip('\n'))

    return sendto_fn

send_to_self_and_guardian = _send_to_combination([send_to_self, send_to_guardian])
send_to_self_and_guardian.__name__ = "send_to_self_and_guardian"
#send_to_self_and_guardian.__doc__ = \
#    "Returns two addresses, the user's own address and its guardian."

send_to_self_and_emergency = _send_to_combination([send_to_self, send_to_emergency])
send_to_self_and_emergency.__name__ = "send_to_self_and_emergency"
#send_to_self_and_emergency.__doc__ = \
#    "Returns two addresses, the user's own address and its emergency contact."

send_to_guardian_and_emergency = _send_to_combination([send_to_guardian, send_to_emergency])
send_to_guardian_and_emergency.__name__ = "send_to_guardian_and_emergency"
#send_to_guardian_and_emergency.__doc__ = \
#    "Returns two addresses, the user's guardian and emergency contact."

send_to_self_and_guardian_and_emergency = _send_to_combination([send_to_self,
                                                                send_to_guardian,
                                                                send_to_emergency])
send_to_self_and_guardian_and_emergency.__name__ = "send_to_self_and_guardian_and_emergency"
#send_to_self_and_guardian_and_emergency.__doc__ = \
#    "Returns three addresses, the user's own address, its guardian, and its emergency contact."

