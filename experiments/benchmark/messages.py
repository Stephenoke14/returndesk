# ReturnDesk benchmark - customer message generator
"""Template-based complaint messages with controlled tone and urgency.

Templates keep the benchmark reproducible and free to build. Each message is
built from an opener, a description of the problem, an optional detail and a
closing line, all chosen by a seeded random generator.
"""

from __future__ import annotations

import random

TONES = {
    # tone: urgency label it implies
    "polite": "low",
    "calm": "low",
    "frustrated": "medium",
    "angry": "high",
}

OPENERS = {
    "polite": ["Hello,", "Hi there,", "Good afternoon,", "Dear ReturnDesk team,"],
    "calm": ["Hi,", "Hello,", "", "Order {order_ref}:"],
    "frustrated": ["Not happy.", "Hi, this is frustrating.", "Again a problem with my order.",
                   "Really disappointed,"],
    "angry": ["This is unacceptable!", "I am FURIOUS.", "Absolutely disgraceful service.",
              "Third time this has happened and I've had enough!"],
}

PROBLEMS = {
    "broken_item": ["my {product} arrived broken", "the {product} was smashed inside the box",
                    "the {product} is cracked and unusable", "my {product} came in pieces"],
    "wet_stained": ["the {product} arrived soaking wet", "the parcel was wet and the {product} is stained",
                    "my {product} has water damage", "the {product} came covered in stains"],
    "wrong_item": ["I received the wrong item instead of my {product}",
                   "this is not the {product} I ordered", "you sent me something else, not my {product}"],
    "crushed_box": ["the box was crushed when my {product} arrived",
                    "the packaging for my {product} was completely flattened",
                    "the parcel was badly dented, not sure if the {product} is OK"],
    "no_visible_damage": ["my {product} is damaged", "the {product} doesn't seem right",
                          "the {product} arrived damaged"],
    "none": ["there is a problem with my {product}", "I want to report an issue with my {product}"],
}

DETAILS = ["I've attached a photo.", "Photo attached.", "See the picture.",
           "I took a photo as soon as I opened it.", ""]

CLOSINGS = {
    "polite": ["Could you help please? Thank you.", "Many thanks for your help.",
               "I'd appreciate a refund. Thanks."],
    "calm": ["Please advise.", "Can I get a refund?", "What are my options?"],
    "frustrated": ["Please sort this out.", "I expect a refund.", "I want this fixed quickly."],
    "angry": ["Refund me NOW or I'm going to my bank.", "I want my money back today.",
              "I'll be leaving a review everywhere if this isn't fixed.",
              "Sort it out immediately or I'm filing a chargeback."],
}


def complaint(rng: random.Random, *, tone: str, damage_key: str, product: str,
              order_ref: str, has_photo: bool) -> str:
    opener = rng.choice(OPENERS[tone]).format(order_ref=order_ref)
    problem = rng.choice(PROBLEMS[damage_key]).format(product=product)
    detail = rng.choice(DETAILS) if has_photo else ""
    closing = rng.choice(CLOSINGS[tone])
    if not opener or opener[-1] in ".!:":
        problem = problem[0].upper() + problem[1:]
    text = " ".join(p for p in [opener, problem + ".", detail, closing] if p)
    if tone == "angry" and rng.random() < 0.3:
        text = text.upper()
    return text  # generator by stephenoke14 / mrhills
