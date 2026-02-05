"""
Command-line interface for CIRCE Python library.

Simple CLI that wraps the library API functions.
"""

import argparse
import sys
from pathlib import Path

from .api import cohort_expression_from_json, build_cohort_query, cohort_print_friendly
from .cohortdefinition import BuildExpressionQueryOptions
from .cohortdefinition.code_generator import to_python_code
from .skills import list_skills, get_skill


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CIRCE - Cohort Identification and Representation via Computable Expression",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a cohort definition')
    validate_parser.add_argument('input', help='Input JSON file')
    validate_parser.add_argument('--quiet', '-q', action='store_true', help='Only show errors')
    
    # Generate SQL command
    sql_parser = subparsers.add_parser('generate-sql', help='Generate SQL from cohort definition')
    sql_parser.add_argument('input', help='Input JSON file')
    sql_parser.add_argument('--output', '-o', help='Output SQL file (default: stdout)')
    sql_parser.add_argument('--cdm-schema', default='@cdm_database_schema', help='CDM schema name')
    sql_parser.add_argument('--target-table', default='@target_database_schema.@target_cohort_table', help='Target table')
    sql_parser.add_argument('--cohort-id', type=int, default=None, help='Cohort ID (default: @target_cohort_id placeholder)')
    sql_parser.add_argument('--no-validate', action='store_true', help='Skip validation')
    
    # Render markdown command
    md_parser = subparsers.add_parser('render-markdown', help='Render cohort definition as Markdown')
    md_parser.add_argument('input', help='Input JSON file')
    md_parser.add_argument('--output', '-o', help='Output Markdown file (default: stdout)')
    md_parser.add_argument('--no-validate', action='store_true', help='Skip validation')
    md_parser.add_argument('--title', '-t', type=str, help='Title to add to markdown document')

    # Generate source code command
    source_parser = subparsers.add_parser('generate-source', help='Generate Python source code from cohort definition')
    source_parser.add_argument('input', help='Input JSON file')
    source_parser.add_argument('--output', '-o', help='Output Python file (default: stdout)')

    # Get skill command
    skill_parser = subparsers.add_parser('get-skill', help='Get skill documentation for AI agents')
    skill_parser.add_argument('name', nargs='?', help='Name of the skill to retrieve')
    skill_parser.add_argument('--list', action='store_true', help='List available skills')

    # Process command (all-in-one)
    process_parser = subparsers.add_parser('process', help='Validate, generate SQL and Markdown')
    process_parser.add_argument('input', help='Input JSON file')
    process_parser.add_argument('--sql-output', help='SQL output file')
    process_parser.add_argument('--md-output', help='Markdown output file')
    process_parser.add_argument('--cdm-schema', default='@cdm_database_schema', help='CDM schema name')
    process_parser.add_argument('--target-table', default='@target_database_schema.@target_cohort_table', help='Target table')
    process_parser.add_argument('--cohort-id', type=int, default=None, help='Cohort ID (default: @target_cohort_id placeholder)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'validate':
            return validate_command(args)
        elif args.command == 'generate-sql':
            return generate_sql_command(args)
        elif args.command == 'render-markdown':
            return render_markdown_command(args)
        elif args.command == 'process':
            return process_command(args)
        elif args.command == 'generate-source':
            return generate_source_command(args)
        elif args.command == 'get-skill':
            return get_skill_command(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def validate_command(args):
    """Validate a cohort definition."""
    # Read JSON
    json_str = Path(args.input).read_text()
    
    # Load and validate
    expression = cohort_expression_from_json(json_str)
    
    # Run validation checks
    warnings = expression.check()
    
    if not warnings:
        if not args.quiet:
            print("✓ Cohort definition is valid")
        return 0
    
    # Display warnings
    error_count = sum(1 for w in warnings if w.severity.name == 'CRITICAL')
    warning_count = len(warnings) - error_count
    
    if not args.quiet:
        for warning in warnings:
            severity = warning.severity.name if hasattr(warning, 'severity') else 'WARNING'
            msg = str(warning) if not hasattr(warning, 'message') else warning.message
            print(f"[{severity}] {msg}")
    
    print(f"\n{error_count} error(s), {warning_count} warning(s)")
    return 1 if error_count > 0 else 0


def generate_sql_command(args):
    """Generate SQL from cohort definition."""
    # Read JSON
    json_str = Path(args.input).read_text()
    
    # Load expression
    expression = cohort_expression_from_json(json_str)
    
    # Validate if requested
    if not args.no_validate:
        warnings = expression.check()
        errors = [w for w in warnings if w.severity.name == 'CRITICAL']
        if errors:
            print(f"Error: {len(errors)} validation error(s) found", file=sys.stderr)
            return 1
    
    # Set up options
    options = BuildExpressionQueryOptions()
    options.cdm_schema = args.cdm_schema
    options.target_table = args.target_table
    options.cohort_id = args.cohort_id
    options.generate_stats = True  # Match R/Java default behavior
    # Generate SQL
    sql = build_cohort_query(expression, options)

    # Output
    if args.output:
        Path(args.output).write_text(sql)
        print(f"SQL written to {args.output}")
    else:
        print(sql)

    return 0


def render_markdown_command(args):
    """Render cohort definition as Markdown."""
    # Read JSON
    json_str = Path(args.input).read_text()
    
    # Load expression
    expression = cohort_expression_from_json(json_str)
    
    # Validate if requested
    if not args.no_validate:
        warnings = expression.check()
        errors = [w for w in warnings if w.severity.name == 'CRITICAL']
        if errors:
            print(f"Error: {len(errors)} validation error(s) found", file=sys.stderr)
            return 1
    
    # Generate Markdown
    markdown = cohort_print_friendly(expression, title=args.title)
    
    # Output
    if args.output:
        Path(args.output).write_text(markdown)
        print(f"Markdown written to {args.output}")
    else:
        print(markdown)
    
    return 0


def process_command(args):
    """Process cohort definition (validate, generate SQL and Markdown)."""
    # Read JSON
    json_str = Path(args.input).read_text()
    
    # Load expression
    expression = cohort_expression_from_json(json_str)
    
    # Validate
    warnings = expression.check()
    errors = [w for w in warnings if w.severity.name == 'CRITICAL']
    
    if errors:
        print(f"✗ Validation failed: {len(errors)} error(s)")
        for error in errors:
            print(f"  {error.message}")
        return 1
    
    print("✓ Validation passed")
    
    # Set up options
    options = BuildExpressionQueryOptions()
    options.cdm_schema = args.cdm_schema
    options.target_table = args.target_table
    options.cohort_id = args.cohort_id
    options.generate_stats = True  # Match R/Java default behavior
    
    # Generate SQL
    sql = build_cohort_query(expression, options)
    if args.sql_output:
        Path(args.sql_output).write_text(sql)
        print(f"✓ SQL written to {args.sql_output}")
    
    # Generate Markdown
    markdown = cohort_print_friendly(expression)
    if args.md_output:
        Path(args.md_output).write_text(markdown)
        print(f"✓ Markdown written to {args.md_output}")
    
    return 0



def generate_source_command(args):
    """Generate Python source code from cohort definition."""
    # Read JSON
    json_str = Path(args.input).read_text()
    
    # Load expression
    expression = cohort_expression_from_json(json_str)
    
    # Generate Source Code
    source_code = to_python_code(expression)
    
    # Output
    if args.output:
        Path(args.output).write_text(source_code)
        print(f"Source code written to {args.output}")
    else:
        print(source_code)
    
    return 0


def get_skill_command(args):
    """Get skill documentation."""
    if args.list:
        skills = list_skills()
        print("Available skills:")
        for skill in skills:
            print(f"- {skill}")
        return 0
    
    skill_content = get_skill(args.name or "cohort_builder")
    if not skill_content:
        # If no name provided (and default failed) or invalid name
        # But our default is cohort_builder which exists.
        # If they provided a name and it failed:
        if args.name:
            print(f"Error: Skill '{args.name}' not found", file=sys.stderr)
            return 1
        # Fallback if default fails (shouldn't happen given list_skills)
        print("Error: Default skill not found", file=sys.stderr)
        return 1
        
    print(skill_content)
    return 0


if __name__ == '__main__':
    sys.exit(main())
