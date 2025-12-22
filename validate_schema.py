import json
from circe import get_json_schema

JAVA_SCHEMA_PATH = "java_cohort_expression_schema.json"
PY_SCHEMA_PATH = "python_cohort_expression_schema.json"


with open(PY_SCHEMA_PATH, "w") as f:
    pyschema = get_json_schema()
    json.dump(pyschema, f, indent=4)


def extract_name_and_type(schema):
    """
    Extract property *names* exactly and their (type / $ref) from each $defs entry.
    """
    out = {}
    defs = schema.get("$defs", {})
    for model_name, model_def in defs.items():
        props = model_def.get("properties", {})
        model_info = {}
        for prop_name, prop_def in props.items():
            # Only keep `$ref` or `type`
            if "$ref" in prop_def:
                model_info[prop_name] = {"$ref": prop_def["$ref"]}
            elif "type" in prop_def:
                model_info[prop_name] = {"type": prop_def["type"]}
            elif "anyOf" in prop_def:
                # If anyOf has a ref or type, include it (but only the first non-null)
                any_ref = next((a["$ref"] for a in prop_def["anyOf"] if "$ref" in a), None)
                any_type = next((a["type"] for a in prop_def["anyOf"] if "type" in a and a["type"] != "null"), None)
                if any_ref:
                    model_info[prop_name] = {"$ref": any_ref}
                elif any_type:
                    model_info[prop_name] = {"type": any_type}
                else:
                    model_info[prop_name] = {}
            else:
                model_info[prop_name] = {}
        out[model_name] = model_info
    return out


def compare_name_and_type(java_info, py_info):
    mismatches = []
    for model_name, java_props in java_info.items():
        if model_name not in py_info:
            mismatches.append(f"❌ Missing model: {model_name}")
            continue

        py_props = py_info[model_name]

        # Check for missing or extra props
        for prop_name in java_props:
            if prop_name not in py_props:
                mismatches.append(f"{model_name}: Missing property '{prop_name}' in Python schema")

        for prop_name in py_props:
            if prop_name not in java_props:
                mismatches.append(f"{model_name}: Extra property '{prop_name}' in Python schema")

        # For common props, compare type/ref exactly
        for prop_name in set(java_props.keys()) & set(py_props.keys()):
            if java_props[prop_name] != py_props[prop_name]:
                mismatches.append(
                    f"{model_name}.{prop_name}: Java {java_props[prop_name]} != Python {py_props[prop_name]}"
                )
    return mismatches


if __name__ == "__main__":
    with open(JAVA_SCHEMA_PATH) as f:
        java_schema = json.load(f)
    with open(PY_SCHEMA_PATH) as f:
        python_schema = json.load(f)

    java_info = extract_name_and_type(java_schema)
    py_info = extract_name_and_type(python_schema)

    diffs = compare_name_and_type(java_info, py_info)

    if diffs:
        print("❌ Name+Type mismatches found:")
        for d in diffs:
            print(" ", d)
    else:
        print("✅ All property names and types match exactly!")