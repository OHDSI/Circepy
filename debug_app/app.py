import os
import sys
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from debug_app import utils

app = Flask(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
COHORTS_DIR = BASE_DIR / 'tests' / 'cohorts'
REFERENCE_DIR = COHORTS_DIR / 'reference_outputs'
TEST_RESULTS_FILE = BASE_DIR / 'debug_app' / 'test_results.json'
USER_OVERRIDES_FILE = BASE_DIR / 'debug_app' / 'user_overrides.json'

@app.route('/')
def index():
    files = sorted([f.name for f in COHORTS_DIR.glob('*.json')])
    
    test_results = {}
    if TEST_RESULTS_FILE.exists():
        try:
            with open(TEST_RESULTS_FILE) as f:
                test_results = json.load(f)
        except Exception as e:
            print(f"Error loading test results: {e}")

    overrides = {}
    if USER_OVERRIDES_FILE.exists():
        try:
            with open(USER_OVERRIDES_FILE) as f:
                overrides = json.load(f)
        except Exception as e:
            print(f"Error loading user overrides: {e}")
            
    # Merge overrides
    # logic: if override[filename] is True, we mark it as user_ok
    for filename, result in test_results.items():
        if overrides.get(filename):
            result['user_ok'] = True
        else:
            result['user_ok'] = False

    # Also make sure overrides are available for files even if test_results missing (though rare)
    for filename, is_ok in overrides.items():
        if filename not in test_results:
            test_results[filename] = {'user_ok': is_ok, 'sql_match': False, 'md_match': False} # Default fail
        elif is_ok:
             test_results[filename]['user_ok'] = True

    return render_template('index.html', files=files, test_results=test_results)

@app.route('/api/override', methods=['POST'])
def toggle_override():
    data = request.json
    filename = data.get('filename')
    is_ok = data.get('is_ok') # Boolean
    
    overrides = {}
    if USER_OVERRIDES_FILE.exists():
         try:
            with open(USER_OVERRIDES_FILE) as f:
                overrides = json.load(f)
         except: pass
         
    overrides[filename] = is_ok
    
    with open(USER_OVERRIDES_FILE, 'w') as f:
        json.dump(overrides, f, indent=2)
        
    return jsonify({"status": "success", "user_ok": is_ok})

@app.route('/cohort/<filename>')
def cohort_view(filename):
    cohort_file = COHORTS_DIR / filename
    if not cohort_file.exists():
        return "File not found", 404
        
    json_content = cohort_file.read_text()
    
    # 1. Generate current state
    result = utils.generate_from_json(json_content)
    
    # 2. Generate Reference using R (dynamic)
    ref_result = utils.generate_reference_with_r(json_content)
    
    # Handle R errors
    if ref_result.get('error'):
         # If R fails, append to existing error or set it
         combined_error = f"{result['error'] or ''}\n\nR Error: {ref_result['error']}".strip()
         result['error'] = combined_error
    
    ref_sql = ref_result['sql']
    ref_md = ref_result['markdown']
    
    # Check overrides
    is_user_ok = False
    if USER_OVERRIDES_FILE.exists():
        try:
            with open(USER_OVERRIDES_FILE) as f:
                overrides = json.load(f)
                is_user_ok = overrides.get(filename, False)
        except: pass

    return render_template('editor.html', 
                           filename=filename,
                           python_code=result['python_code'],
                           gen_sql=result.get('normalized_sql', ''),
                           gen_md=result.get('normalized_markdown', ''),
                           ref_sql=ref_result.get('normalized_sql', ''),
                           ref_md=ref_result.get('normalized_markdown', ''),
                           error=result['error'],
                           is_user_ok=is_user_ok)

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.json
    code = data.get('code')
    
    result = utils.execute_python_code(code)
    
    return jsonify({
        "sql": result.get('normalized_sql', ''),
        "markdown": result.get('normalized_markdown', ''),
        "error": result['error']
    })

@app.route('/explain', methods=['POST'])
def explain_diff():
    data = request.json
    ref_content = data.get('ref')
    gen_content = data.get('gen')
    diff_type = data.get('type', 'SQL')
    
    result = utils.get_ai_explanation(ref_content, gen_content, diff_type)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
