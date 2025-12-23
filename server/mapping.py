# Function for mapping the additive number to a human-readable name (Uses additive_names.json)
def additive_name(additives_tags: list, additives_data: dict) -> list:
    return [additives_data.get(additive, "Unknown") for additive in additives_tags]


# Function for mapping the nova group number to a human-readable name (Used in search.py)
def nova_name(nova_group: int) -> str:
    group_names = {
        1: "Unprocessed or minimally processed foods",
        2: "Processed culinary ingredients",
        3: "Processed foods",
        4: "Ultra-processed food and drink products",
    }
    return group_names.get(nova_group, "Unknown")


# Function for mapping the nutriscore grade to a color code (Used in search.py)
def grade_color(nutriscore_grade: str) -> str:
    grade_colors = {
        "a": "#8AC449",
        "b": "#8FD0FF",
        "c": "#FFD65A",
        "d": "#F8A72C",
        "e": "#DF5656",
    }
    return grade_colors.get(nutriscore_grade.lower(), "gray")


# Function for mapping the nutriscore grade to an assessment category (Used in search.py)
# Uses the official Nutri-Score grade (A-E) provided by OpenFoodFacts API
def score_assessment(nutriscore_grade: str) -> str:
    if not nutriscore_grade:
        return "unknown"

    grade = nutriscore_grade.lower()
    assessment_map = {
        "a": "excellent",
        "b": "good",
        "c": "average",
        "d": "poor",
        "e": "very poor",
    }
    return assessment_map.get(grade, "unknown")


# Function to get primary score (nutriscore priority, fallback to ecoscore)
def primary_score(product_data: dict) -> dict:
    valid_grades = ["a", "b", "c", "d", "e"]

    nutriscore_grade = str(product_data.get("nutriscore_grade", "")).lower()
    ecoscore_grade = str(product_data.get("ecoscore_grade", "")).lower()

    if nutriscore_grade in valid_grades:
        return {
            "grade": nutriscore_grade.upper(),
            "grade_color": grade_color(nutriscore_grade),
            "assessment": score_assessment(nutriscore_grade).title(),
            "score": product_data.get("nutriscore_score"),
            "type": "nutriscore",
        }
    elif ecoscore_grade in valid_grades:
        return {
            "grade": ecoscore_grade.upper(),
            "grade_color": grade_color(ecoscore_grade),
            "assessment": score_assessment(ecoscore_grade).title(),
            "score": product_data.get("ecoscore_score"),
            "type": "ecoscore",
        }
    else:
        return {
            "grade": None,
            "grade_color": "#757575",
            "assessment": "Unknown",
            "score": None,
            "type": None,
        }


# Function for getting the icon based on the category map (Used in utils.py)
def food_icon(name: str, category_map: dict) -> str:
    for category, items in category_map.items():
        if name in items:
            return category.lower().replace(" ", "-")
    return name.lower().replace(" ", "-")
