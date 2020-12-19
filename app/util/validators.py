import re
import logging

from app.exceptions.data import HTTPBadRequest

logger = logging.getLogger(__name__)


def validate_mail(mail):
    regex = r"(?:[a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"

    matches = re.finditer(regex, mail, re.MULTILINE)

    for matchNum, match in enumerate(matches, start=1):
        logger.debug("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum=matchNum,
                                                                                   start=match.start(),
                                                                                   end=match.end(),
                                                                                   match=match.group()))
        return match.group()
    return None


def receiver_dict_validator(rec, required=True):
    if not rec:
        return rec
    if ("amera" not in rec and "external" not in rec)\
            or (rec["amera"] and type(rec["amera"]) != list)\
            or (rec["external"] and type(rec["external"]) != list):
        raise HTTPBadRequest("Invalid data for receivers")

    if rec["amera"]:
        rec["amera"] = [i for i in rec["amera"] if i]
    else:
        rec["amera"] = []
    if rec["external"]:
        rec["external"] = [i for i in rec["external"] if i]
    else:
        rec["external"] = []
    if len(rec["amera"]) + len(rec["external"]) < 1 and required:
        raise HTTPBadRequest("Receiver list is empty")
    return {
        "amera": rec["amera"] if rec["amera"] else [],
        "external": rec["external"] if rec["external"] else [],
    }
