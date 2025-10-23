#!/usr/bin/env python3
"""
Java CIRCE-BE Schema Analysis Script (Simplified)

This script manually parses Java source files to extract:
1. Class definitions and their fields
2. Field types and annotations
3. A comprehensive JSON schema for cohort expressions
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class JavaField:
    """Represents a Java field"""
    name: str
    type: str
    is_optional: bool = False
    is_static: bool = False
    is_final: bool = False
    annotations: List[str] = None
    default_value: Optional[str] = None
    
    def __post_init__(self):
        if self.annotations is None:
            self.annotations = []


@dataclass
class JavaClass:
    """Represents a Java class"""
    name: str
    package: str
    full_name: str
    fields: List[JavaField] = None
    superclass: Optional[str] = None
    interfaces: List[str] = None
    is_interface: bool = False
    is_abstract: bool = False
    annotations: List[str] = None
    modifiers: List[str] = None
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = []
        if self.interfaces is None:
            self.interfaces = []
        if self.annotations is None:
            self.annotations = []
        if self.modifiers is None:
            self.modifiers = []


class JavaSchemaAnalyzer:
    """Analyzes Java source code and extracts schema information"""
    
    def __init__(self, source_path: str):
        self.source_path = Path(source_path)
        self.classes: Dict[str, JavaClass] = {}
        self.package_hierarchy: Dict[str, List[str]] = defaultdict(list)
        
    def is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test file"""
        return (
            'test' in str(file_path).lower() or
            file_path.name.endswith('Test.java') or
            '/test/' in str(file_path)
        )
    
    def extract_package_from_path(self, file_path: Path) -> str:
        """Extract package name from file path"""
        parts = file_path.parts
        java_idx = None
        
        # Find the 'java' directory
        for i, part in enumerate(parts):
            if part == 'java':
                java_idx = i
                break
        
        if java_idx is None:
            return ""
        
        # Get the package parts after 'java'
        package_parts = parts[java_idx + 1:-1]  # Exclude the filename
        return '.'.join(package_parts)
    
    def parse_java_file(self, file_path: Path) -> Optional[JavaClass]:
        """Parse a single Java file and extract class information"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract package
            package_match = re.search(r'package\s+([^;]+);', content)
            package = package_match.group(1) if package_match else self.extract_package_from_path(file_path)
            
            # Find class declarations
            class_pattern = r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)'
            interface_pattern = r'(?:public\s+)?interface\s+(\w+)'
            
            class_matches = re.findall(class_pattern, content)
            interface_matches = re.findall(interface_pattern, content)
            
            if not class_matches and not interface_matches:
                return None
            
            # Take the first class/interface found
            class_name = (class_matches + interface_matches)[0]
            is_interface = len(interface_matches) > 0 and interface_matches[0] == class_name
            
            full_name = f"{package}.{class_name}" if package else class_name
            
            java_class = JavaClass(
                name=class_name,
                package=package,
                full_name=full_name,
                is_interface=is_interface
            )
            
            # Extract fields
            self._extract_fields(content, java_class)
            
            # Extract superclass and interfaces
            self._extract_inheritance(content, java_class)
            
            return java_class
                    
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _extract_fields(self, content: str, java_class: JavaClass):
        """Extract fields from Java class content"""
        # Pattern to match field declarations
        # Matches: [modifiers] [type] [name] [= value];
        field_pattern = r'(?:@\w+(?:\([^)]*\))?\s*)*\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?\s*([^=\s]+)\s+(\w+)\s*(?:=\s*[^;]+)?;'
        
        # Also match fields with annotations
        annotated_field_pattern = r'(?:@\w+(?:\([^)]*\))?\s*)*\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?\s*([^=\s]+)\s+(\w+)\s*(?:=\s*[^;]+)?;'
        
        # Find all field matches
        field_matches = re.findall(field_pattern, content, re.MULTILINE)
        annotated_matches = re.findall(annotated_field_pattern, content, re.MULTILINE)
        
        # Combine and deduplicate
        all_matches = list(set(field_matches + annotated_matches))
        
        for field_type, field_name in all_matches:
            # Skip method parameters and local variables
            if '(' in field_type or ')' in field_type:
                continue
            
            # Clean up field type
            field_type = field_type.strip()
            
            # Skip if it looks like a method
            if field_name in ['main', 'toString', 'equals', 'hashCode']:
                continue
            
            # Extract annotations for this field
            annotations = self._extract_field_annotations(content, field_name)
            
            # Determine if field is optional
            is_optional = self._is_optional_field(field_type, annotations)
            
            java_field = JavaField(
                name=field_name,
                type=field_type,
                is_optional=is_optional,
                annotations=annotations
            )
            
            java_class.fields.append(java_field)
    
    def _extract_field_annotations(self, content: str, field_name: str) -> List[str]:
        """Extract annotations for a specific field"""
        annotations = []
        
        # Look for annotations before the field declaration
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if field_name in line and ('=' in line or ';' in line):
                # Look backwards for annotations
                j = i - 1
                while j >= 0:
                    line_before = lines[j].strip()
                    if line_before.startswith('@'):
                        annotation = line_before.split('(')[0].replace('@', '')
                        annotations.append(annotation)
                    elif line_before == '' or line_before.startswith('//'):
                        j -= 1
                        continue
                    else:
                        break
                    j -= 1
                break
        
        return annotations
    
    def _extract_inheritance(self, content: str, java_class: JavaClass):
        """Extract superclass and interfaces"""
        # Extract extends clause
        extends_match = re.search(r'extends\s+(\w+)', content)
        if extends_match:
            java_class.superclass = extends_match.group(1)
        
        # Extract implements clause
        implements_match = re.search(r'implements\s+([^{]+)', content)
        if implements_match:
            interfaces_str = implements_match.group(1)
            interfaces = [iface.strip() for iface in interfaces_str.split(',')]
            java_class.interfaces = interfaces
    
    def _is_optional_field(self, field_type: str, annotations: List[str]) -> bool:
        """Determine if a field is optional"""
        # Check for Optional<T> wrapper
        if 'Optional<' in field_type:
            return True
        
        # Check for nullable annotations
        nullable_annotations = ['Nullable', 'Optional']
        for annotation in annotations:
            if any(nullable in annotation for nullable in nullable_annotations):
                return True
        
        # Primitive types are not optional
        primitive_types = ['int', 'long', 'short', 'byte', 'float', 'double', 'boolean', 'char']
        if field_type.lower() in primitive_types:
            return False
        
        return True
    
    def analyze_source_directory(self):
        """Analyze all Java files in the source directory"""
        print("🔍 Analyzing Java source code...")
        
        java_files = list(self.source_path.rglob("*.java"))
        non_test_files = [f for f in java_files if not self.is_test_file(f)]
        
        print(f"📁 Found {len(java_files)} Java files")
        print(f"📁 Found {len(non_test_files)} non-test Java files")
        
        for file_path in non_test_files:
            java_class = self.parse_java_file(file_path)
            if java_class:
                self.classes[java_class.full_name] = java_class
                self.package_hierarchy[java_class.package].append(java_class.name)
        
        print(f"✅ Parsed {len(self.classes)} classes")
    
    def generate_cohort_expression_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for cohort expression based on Java classes"""
        print("📋 Generating CohortExpression JSON schema...")
        
        # Find the main CohortExpression class
        cohort_expr_class = None
        for class_name, java_class in self.classes.items():
            if java_class.name == 'CohortExpression':
                cohort_expr_class = java_class
                break
        
        if not cohort_expr_class:
            print("❌ CohortExpression class not found!")
            return {}
        
        # Build schema definitions for all related classes
        definitions = {}
        processed_classes = set()
        
        def add_class_to_definitions(class_name: str):
            """Recursively add class and its dependencies to definitions"""
            if class_name in processed_classes:
                return
            
            # Find the class
            java_class = None
            for full_name, cls in self.classes.items():
                if cls.name == class_name:
                    java_class = cls
                    break
            
            if not java_class:
                return
            
            processed_classes.add(class_name)
            
            # Create schema for this class
            properties = {}
            required_fields = []
            
            for field in java_class.fields:
                field_schema = self._field_to_json_schema(field)
                properties[field.name] = field_schema
                
                # Determine if field is required
                if not field.is_optional:
                    required_fields.append(field.name)
            
            class_schema = {
                "type": "object",
                "description": f"Java class: {java_class.full_name}",
                "properties": properties
            }
            
            if required_fields:
                class_schema["required"] = required_fields
            
            definitions[class_name] = class_schema
            
            # Process field types recursively
            for field in java_class.fields:
                field_type = self._extract_simple_type(field.type)
                if field_type and field_type not in processed_classes:
                    add_class_to_definitions(field_type)
        
        # Start with CohortExpression and process all dependencies
        add_class_to_definitions('CohortExpression')
        
        # Create the main schema
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://github.com/OHDSI/circe-be/java-schema.json",
            "title": "CIRCE-BE Java Implementation Schema",
            "description": "JSON Schema extracted from Java CIRCE-BE source code",
            "version": "1.0.0",
            "definitions": definitions,
            "properties": {
                "cohortExpression": {
                    "$ref": "#/$defs/CohortExpression"
                }
            },
            "type": "object"
        }
        
        return schema
    
    def _field_to_json_schema(self, field: JavaField) -> Dict[str, Any]:
        """Convert Java field to JSON schema property"""
        field_type = field.type.lower()
        
        # Map Java types to JSON schema types
        if field_type in ['string', 'char']:
            schema_type = "string"
        elif field_type in ['int', 'integer', 'long', 'short', 'byte']:
            schema_type = "integer"
        elif field_type in ['float', 'double', 'bigdecimal']:
            schema_type = "number"
        elif field_type == 'boolean':
            schema_type = "boolean"
        elif field_type.endswith('[]'):
            # Array type
            element_type = field_type[:-2]
            return {
                "type": "array",
                "items": self._field_to_json_schema(JavaField("", element_type))
            }
        elif field_type in ['list', 'arraylist', 'linkedlist']:
            return {
                "type": "array",
                "items": {"type": "object"}
            }
        elif field_type in ['map', 'hashmap', 'linkedhashmap']:
            return {
                "type": "object",
                "additionalProperties": True
            }
        else:
            # Custom class type
            schema_type = "object"
        
        property_schema = {
            "type": schema_type,
            "description": f"Field: {field.name} ({field.type})"
        }
        
        # Add reference for custom types
        if schema_type == "object" and not field_type.endswith('[]'):
            simple_type = self._extract_simple_type(field.type)
            if simple_type:
                property_schema["$ref"] = f"#/$defs/{simple_type}"
        
        return property_schema
    
    def _extract_simple_type(self, java_type: str) -> Optional[str]:
        """Extract simple type name from Java type"""
        # Remove generics and array brackets
        simple_type = java_type.split('<')[0].split('[')[0]
        
        # Remove package prefix if present
        if '.' in simple_type:
            simple_type = simple_type.split('.')[-1]
        
        return simple_type
    
    def generate_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        print("📊 Generating analysis report...")
        
        # Class statistics
        total_classes = len(self.classes)
        interfaces = sum(1 for cls in self.classes.values() if cls.is_interface)
        abstract_classes = sum(1 for cls in self.classes.values() if cls.is_abstract)
        
        # Package statistics
        package_stats = {}
        for package, classes in self.package_hierarchy.items():
            package_stats[package] = {
                "class_count": len(classes),
                "classes": classes
            }
        
        # Field statistics
        total_fields = sum(len(cls.fields) for cls in self.classes.values())
        
        report = {
            "metadata": {
                "source_path": str(self.source_path),
                "analysis_timestamp": "2024-01-01T00:00:00Z",
                "total_files_analyzed": len(list(self.source_path.rglob("*.java")))
            },
            "statistics": {
                "total_classes": total_classes,
                "interfaces": interfaces,
                "abstract_classes": abstract_classes,
                "total_fields": total_fields,
                "packages": len(self.package_hierarchy)
            },
            "package_hierarchy": package_stats,
            "classes": {name: asdict(cls) for name, cls in self.classes.items()}
        }
        
        return report


def main():
    """Main function"""
    print("🚀 Java CIRCE-BE Schema Analysis (Simplified)")
    print("=" * 50)
    
    # Initialize analyzer
    source_path = "circe-be/src/main/java"
    analyzer = JavaSchemaAnalyzer(source_path)
    
    # Analyze source code
    analyzer.analyze_source_directory()
    
    # Generate cohort expression schema
    schema = analyzer.generate_cohort_expression_schema()
    
    # Generate analysis report
    report = analyzer.generate_analysis_report()
    
    # Save results
    schema_file = "java_cohort_expression_schema.json"
    report_file = "java_analysis_report.json"
    
    with open(schema_file, 'w') as f:
        json.dump(schema, f, indent=2)
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Analysis complete!")
    print(f"📄 Schema saved to: {schema_file}")
    print(f"📄 Report saved to: {report_file}")
    print(f"📊 Analyzed {len(analyzer.classes)} classes")
    print(f"📊 Found {len(analyzer.package_hierarchy)} packages")


if __name__ == "__main__":
    main()
