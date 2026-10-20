"""Indian food library used by the lifestyle simulator.

carbs_g : available carbohydrate per typical portion (approximate, rounded).
gi      : glycaemic index (glucose = 100).

GI sources: values marked "Henry2021" come from Henry, C. J. et al. (2021),
"A glycaemic index compendium of non-western foods", Nutrition & Diabetes 11:2
(white rice range 79-96; rice dosa 76; upma 71; idli 62-85 across studies).
Values marked "NIN" are National Institute of Nutrition (ICMR) measurements as
reported in the press (chapati 62, plain dosa 79). Values marked "assumed" are
our simulation assumptions and are NOT measured values. Portion carbohydrate
values are approximations for simulation only, not dietary advice.
"""

FOODS = {
    # name:            (carbs_g, gi,  source)
    "white_rice_katori": (45, 79, "Henry2021"),
    "chapati":          (18, 62, "NIN"),
    "idli":             (13, 67, "Henry2021"),
    "plain_dosa":       (30, 76, "Henry2021"),
    "poha_plate":       (45, 74, "Henry2021"),
    "upma_plate":       (40, 71, "Henry2021"),
    "aloo_paratha":     (35, 65, "assumed"),
    "dal_katori":       (18, 35, "assumed"),
    "sambar_katori":    (10, 40, "assumed"),
    "sabzi_katori":     (10, 40, "assumed"),
    "curd_katori":      (5, 35, "assumed"),
    "biryani_plate":    (70, 70, "assumed"),
    "pongal_plate":     (45, 70, "assumed"),
    "bread_slice":      (13, 70, "assumed"),
    "chai_with_sugar":  (12, 65, "assumed (sucrose)"),
    "biscuits_2":       (15, 70, "assumed"),
    "samosa":           (30, 60, "assumed"),
    "banana":           (25, 51, "assumed"),
    "apple":            (20, 36, "assumed"),
    "gulab_jamun_2":    (45, 75, "assumed"),
}

# Meal templates by region: lists of (food, portions). Portions are scaled per person.
MEALS = {
    "north": {
        "breakfast": [[("aloo_paratha", 2), ("curd_katori", 1)], [("poha_plate", 1), ("chai_with_sugar", 1)],
                      [("bread_slice", 2), ("chai_with_sugar", 1)], [("upma_plate", 1), ("chai_with_sugar", 1)]],
        "lunch": [[("chapati", 3), ("dal_katori", 1), ("sabzi_katori", 1)],
                  [("white_rice_katori", 1.5), ("dal_katori", 1), ("sabzi_katori", 1)],
                  [("chapati", 2), ("white_rice_katori", 1), ("dal_katori", 1)]],
        "dinner": [[("chapati", 3), ("dal_katori", 1), ("sabzi_katori", 1)],
                   [("chapati", 2), ("white_rice_katori", 1), ("sabzi_katori", 1)],
                   [("biryani_plate", 1), ("curd_katori", 1)]],
    },
    "south": {
        "breakfast": [[("idli", 3), ("sambar_katori", 1)], [("plain_dosa", 2), ("sambar_katori", 1)],
                      [("upma_plate", 1), ("chai_with_sugar", 1)], [("pongal_plate", 1)]],
        "lunch": [[("white_rice_katori", 2), ("sambar_katori", 1), ("sabzi_katori", 1)],
                  [("white_rice_katori", 2), ("dal_katori", 1), ("curd_katori", 1)]],
        "dinner": [[("white_rice_katori", 1.5), ("sambar_katori", 1), ("sabzi_katori", 1)],
                   [("plain_dosa", 2), ("sambar_katori", 1)], [("chapati", 2), ("sabzi_katori", 1)],
                   [("biryani_plate", 1), ("curd_katori", 1)]],
    },
    "snack": [[("chai_with_sugar", 1), ("biscuits_2", 1)], [("chai_with_sugar", 1)], [("samosa", 1), ("chai_with_sugar", 1)],
              [("banana", 1)], [("apple", 1)]],
    "sweet": [[("gulab_jamun_2", 1)]],
}


def meal_totals(items, scale=1.0):
    """Return (carbs_g, carb-weighted GI) for a list of (food, portions)."""
    carbs = 0.0
    gi_w = 0.0
    for food, n in items:
        c, gi, _ = FOODS[food]
        c = c * n * scale
        carbs += c
        gi_w += c * gi
    return carbs, (gi_w / carbs if carbs > 0 else 50.0)


def describe(items, scale=1.0):
    parts = []
    for food, n in items:
        k = n * scale
        parts.append(f"{k:.1f} x {food.replace('_', ' ')}" if abs(k - round(k)) > 0.05 else f"{int(round(k))} x {food.replace('_', ' ')}")
    return ", ".join(parts)
