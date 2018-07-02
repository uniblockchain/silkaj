from os import system
from time import time
from tabulate import tabulate
from collections import OrderedDict

from silkaj.network_tools import get_request
from silkaj.tools import message_exit, check_public_key, convert_time
from silkaj.constants import NO_MATCHING_ID


def get_sent_certifications(certs, time_first_block, params):
    sent = list()
    expire = list()
    if certs["signed"]:
        for cert in certs["signed"]:
            sent.append(cert["uid"])
            expire.append(expiration_date_from_block_id(cert["cert_time"]["block"], time_first_block, params))
    return sent, expire


def received_sent_certifications(ep, id):
    """
    check id exist
    many identities could exist
    retrieve the one searched
    get id of received and sent certifications
    display on a chart the result with the numbers
    """
    params = get_request(ep, "blockchain/parameters")
    time_first_block = get_request(ep, "blockchain/block/1")["time"]
    if get_pubkeys_from_id(ep, id) == NO_MATCHING_ID:
        message_exit(NO_MATCHING_ID)
    certs_req = get_request(ep, "wot/lookup/" + id)["results"]
    for certs_id in certs_req:
        if certs_id['uids'][0]['uid'].lower() == id.lower():
            id_certs = certs_id
            break
    certifications = OrderedDict()
    system("clear")
    for certs in id_certs["uids"]:
        if certs["uid"].lower() == id.lower():
            pubkey = id_certs["pubkey"]
            req = get_request(ep, "wot/requirements/" + pubkey)["identities"][0]
            certifications["received_expire"] = list()
            certifications["received"] = list()
            for cert in certs["others"]:
                certifications["received_expire"].append(expiration_date_from_block_id(cert["meta"]["block_number"], time_first_block, params))
                certifications["received"].append(cert_written_in_the_blockchain(req["certifications"], cert))
                certifications["sent"], certifications["sent_expire"] = get_sent_certifications(id_certs, time_first_block, params)
            nbr_sent_certs = len(certifications["sent"]) if "sent" in certifications else 0
            print("{0} ({1}) from block #{2}\nreceived {3} and sent {4}/{5} certifications:\n{6}\n"
                    .format(id, pubkey[:5] + "…", certs["meta"]["timestamp"][:15] + "…",
                        len(certifications["received"]), nbr_sent_certs, params["sigStock"],
                        tabulate(certifications, headers="keys", tablefmt="orgtbl", stralign="center")))
            membership_status(ep, params, certifications, certs, pubkey, req)


def cert_written_in_the_blockchain(written_certs, certifieur):
    for cert in written_certs:
        if cert["from"] == certifieur["pubkey"]:
            return certifieur["uids"][0] + " ✔"
    return certifieur["uids"][0]


def membership_status(ep, params, certifications, certs, pubkey, req):
    if len(certifications["received"]) >= params["sigQty"]:
        print("Membership expiration due to certifications expirations: " + certifications["received_expire"][len(certifications["received"]) - params["sigQty"]])
    member = is_member(ep, pubkey, certs["uid"])
    print("member:", member)
    if not member and req["wasMember"]:
        print("revoked:", req["revoked"], "\nrevoked on:", req["revoked_on"], "\nexpired:", req["expired"], "\nwasMember:", req["wasMember"])
    elif member:
        print("Membership document expiration: " + convert_time(time() + req["membershipExpiresIn"], "date"))
        print("Sentry:", req["isSentry"])
    print("outdistanced:", req["outdistanced"])


def expiration_date_from_block_id(block_id, time_first_block, params):
    return convert_time(date_approximation(block_id, time_first_block, params["avgGenTime"]) + params["sigValidity"], "date")


def date_approximation(block_id, time_first_block, avgentime):
    return time_first_block + block_id * avgentime


def id_pubkey_correspondence(ep, id_pubkey):
    if check_public_key(id_pubkey, False):
        print("{} public key corresponds to identity: {}".format(id_pubkey, get_uid_from_pubkey(ep, id_pubkey)))
    else:
        pubkeys = get_pubkeys_from_id(ep, id_pubkey)
        if pubkeys == NO_MATCHING_ID:
            print(NO_MATCHING_ID)
        else:
            print("Public keys found matching '{}':\n".format(id_pubkey))
            for pubkey in pubkeys:
                print("→", pubkey["pubkey"], end=" ")
                try:
                    print("↔ " + get_request(ep, "wot/identity-of/" + pubkey["pubkey"])["uid"])
                except:
                    print("")


def get_uid_from_pubkey(ep, pubkey):
    try:
        results = get_request(ep, "wot/lookup/" + pubkey)
    except:
        return NO_MATCHING_ID
    i, results = 0, results["results"]
    while i < len(results):
        if results[i]["uids"][0]["uid"] != pubkey:
            return results[i]["uids"][0]["uid"]
        i += 1


def get_pubkeys_from_id(ep, uid):
    try:
        results = get_request(ep, "wot/lookup/" + uid)
    except:
        return NO_MATCHING_ID
    return results["results"]


def is_member(ep, pubkey, uid):
    members = get_request(ep, "wot/members")["results"]
    for member in members:
        if (pubkey in member["pubkey"] and uid in member["uid"]):
            return(True)
    return(False)


def get_pubkey_from_id(ep, uid):
    members = get_request(ep, "wot/members")["results"]
    for member in members:
        if (uid == member["uid"]):
            return(member["pubkey"])
    return(NO_MATCHING_ID)