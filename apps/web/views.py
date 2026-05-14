from django.http import JsonResponse
from django.shortcuts import render

from apps.billing.services import ensure_beta_credit_packs


EXAMPLES = [
    {
        "title": "Funky Birthday Song for Mike",
        "occasion": "Birthday",
        "vibe": "Funky Groove",
        "snippet": "Mike walks in late but somehow steals the show",
        "duration": "0:15",
    },
    {
        "title": "Sweet Graduation Song for Ava",
        "occasion": "Graduation",
        "vibe": "Acoustic Sweet",
        "snippet": "Ava, you made the hard days sing",
        "duration": "0:15",
    },
    {
        "title": "Promotion Anthem for Jess",
        "occasion": "Promotion",
        "vibe": "Pop Anthem",
        "snippet": "Jess got the title and the group chat crown",
        "duration": "0:15",
    },
    {
        "title": "Light Roast for Danny",
        "occasion": "Roast",
        "vibe": "Club Banger",
        "snippet": "Danny says five minutes, see you next year",
        "duration": "0:15",
    },
]


def home(request):
    packs = ensure_beta_credit_packs()
    return render(request, "web/home.html", {"examples": EXAMPLES, "packs": packs})


def health(request):
    return JsonResponse({"ok": True})
