#!/usr/bin/env python3

import argparse
import csv
import sys
import yaml
import re
import os

# Define the version number
VERSION = '0.2'


def process_csv(input_file, output_file, odoo_version):
    with open(input_file, 'r', newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        headers = next(csv_reader)

        data_dict = {}

        for i, row in enumerate(csv_reader, start=2):  # Start at line 2 (since we skipped header)
            if not re.search(r'\(\d+ rows\)', row[0]):
                if len(row) >= 4:
                    name = row[0]
                    author = row[1]  # Extracted author value from index 1
                    if name in data_dict:
                        existing_data = data_dict[name]
                        odoo_data = {
                            headers[2]: row[2],
                            headers[3]: row[3],
                        }
                        existing_odoo_data = existing_data.get(odoo_version, {})
                        odoo_data["evaluation"] = existing_odoo_data.get("evaluation", "")
                        odoo_data["comment"] = existing_odoo_data.get("comment", "")
                        existing_data[odoo_version].update(odoo_data)
                    else:
                        data_dict[name] = {
                            "name": name,
                            "author": author,
                            odoo_version: {
                                headers[2]: row[2],
                                headers[3]: row[3],
                                "evaluation": "",
                                "comment": ""
                            }
                    }

                else:
                    print(f"Skipping row {i}: {row}. It doesn't have enough columns.")
            else:
                print(f"Skipping row {i}: {row}. It contains the pattern '(<number> rows)'.")

    try:
        with open(output_file, 'r') as existing_yaml_file:
            existing_data = yaml.safe_load(existing_yaml_file)
            if existing_data is None:
                existing_data = []

        # Track which modules were found in the CSV
        csv_module_names = set(data_dict.keys())

        for name, new_data in data_dict.items():
            index = next((i for i, item in enumerate(existing_data) if item['name'] == name), None)
            if index is not None:
                new_data[odoo_version]["evaluation"] = existing_data[index].get(odoo_version, {}).get("evaluation", "")
                new_data[odoo_version]["comment"] = existing_data[index].get(odoo_version, {}).get("comment", "")
                existing_data[index].setdefault(odoo_version, {}).update(new_data[odoo_version])
            else:
                existing_data.append(new_data)

        # Handle modules that exist in YAML but not in CSV - set their state to "not installed"
        for entry in existing_data:
            entry_name = entry.get('name')
            if entry_name and entry_name not in csv_module_names:
                # Module exists in YAML but not in CSV, set state to "not installed"
                # Check for both string and numeric version keys to handle YAML parsing variations
                version_key = None
                for key in entry.keys():
                    if str(key) == odoo_version:
                        version_key = key
                        break
                
                if version_key:
                    entry[version_key]['state'] = 'not installed'
                else:
                    # If the version doesn't exist, create it with "not installed" state
                    entry[odoo_version] = {
                        'state': 'not installed',
                        'auto_install': '',
                        'evaluation': '',
                        'comment': ''
                    }

        # Sort entries alphabetically by name and sort version keys within each entry
        existing_data.sort(key=lambda x: x.get('name', ''))
        for entry in existing_data:
            # Sort version keys with highest version first
            version_keys = [k for k in entry.keys() if k not in ['name', 'author']]
            version_keys.sort(key=lambda x: [int(i) for i in str(x).split('.')], reverse=True)
            
            # Reorder the entry dictionary
            ordered_entry = {'name': entry['name'], 'author': entry['author']}
            for version in version_keys:
                ordered_entry[version] = entry[version]
            entry.clear()
            entry.update(ordered_entry)

        with open(output_file, 'w') as yaml_file:
            yaml.dump(existing_data, yaml_file, default_flow_style=False, sort_keys=False, width=float('inf'))

        print(f"Data appended/merged to {output_file} successfully.")
    except FileNotFoundError:
        with open(output_file, 'w') as yaml_file:
            yaml.dump([data for name, data in data_dict.items()], yaml_file, default_flow_style=False, sort_keys=False, width=float('inf'))
        print(f"{output_file} not found. Created a new file with the data.")
    except Exception as e:
        print(f"An error occurred: {e}")


def compare_versions(yaml_file, source_version, target_version):
    with open(yaml_file, 'r') as yaml_file:
        data = yaml.safe_load(yaml_file)

    if not isinstance(data, list):
        print("Error: YAML file must contain a list of dictionaries.")
        return

    for entry in data:
        name = entry.get('name')
        if name:
            source_data = entry.get(source_version)
            target_data = entry.get(target_version)

            if source_data and target_data:
                if source_data.get('state') != target_data.get('state'):
                    print(f"Name: {name}, State in {source_version}: {source_data.get('state')}, State in {target_version}: {target_data.get('state')}")


def add_version(yaml_file_path, odoo_version):
    try:
        with open(yaml_file_path, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)

        if not isinstance(data, list):
            print("Error: YAML file must contain a list of dictionaries.")
            return

        # Define the keys to pre-populate
        keys_to_prepopulate = ['state', 'auto_install', 'evaluation', 'comment']

        for entry in data:
            entry[odoo_version] = {key: '' for key in keys_to_prepopulate}

        # Sort entries alphabetically by name and sort version keys within each entry
        data.sort(key=lambda x: x.get('name', ''))
        for entry in data:
            # Sort version keys with highest version first
            version_keys = [k for k in entry.keys() if k not in ['name', 'author']]
            version_keys.sort(key=lambda x: [int(i) for i in str(x).split('.')], reverse=True)
            
            # Reorder the entry dictionary
            ordered_entry = {'name': entry['name'], 'author': entry['author']}
            for version in version_keys:
                ordered_entry[version] = entry[version]
            entry.clear()
            entry.update(ordered_entry)

        with open(yaml_file_path, 'w') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False, sort_keys=False, width=float('inf'))

        print(f"Added version '{odoo_version}' with pre-populated keys to all entries in '{yaml_file_path}'.")
    except Exception as e:
        print(f"An error occurred: {e}")


def remove_version(yaml_file_path, odoo_version):
    try:
        with open(yaml_file_path, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)

        if not isinstance(data, list):
            print("Error: YAML file must contain a list of dictionaries.")
            return

        for entry in data:
            entry.pop(odoo_version, None)

        # Sort entries alphabetically by name and sort version keys within each entry
        data.sort(key=lambda x: x.get('name', ''))
        for entry in data:
            # Sort version keys with highest version first
            version_keys = [k for k in entry.keys() if k not in ['name', 'author']]
            version_keys.sort(key=lambda x: [int(i) for i in str(x).split('.')], reverse=True)
            
            # Reorder the entry dictionary
            ordered_entry = {'name': entry['name'], 'author': entry['author']}
            for version in version_keys:
                ordered_entry[version] = entry[version]
            entry.clear()
            entry.update(ordered_entry)

        with open(yaml_file_path, 'w') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False, sort_keys=False, width=float('inf'))

        print(f"Removed version '{odoo_version}' from all entries in '{yaml_file_path}'.")
    except Exception as e:
        print(f"An error occurred: {e}")


def analyse(yaml_file, odoo_version, include_authors=None, exclude_authors=None):
    try:
        with open(yaml_file, 'r') as existing_yaml_file:
            existing_data = yaml.safe_load(existing_yaml_file)
            if existing_data is None:
                existing_data = []

        # Dictionary to group modules by their state
        state_groups = {
            'Not evaluated': [],
            'Required but not installed': [],
            'Desired but not installed': [],
            'Not desired but installed': [],
            'Not required but installed': []
        }
        
        required_and_migrated_count = 0

        for entry in existing_data:
            entry_data = entry.get(odoo_version, {})
            state = entry_data.get('state', '')
            evaluation = entry_data.get('evaluation', '')
            name = entry.get('name', '')
            author = entry.get('author', '')

            # Apply author filtering
            if include_authors:
                # Check if any of the include_authors is found in the author field (case-insensitive, partial match)
                if not any(inc_author.lower() in author.lower() for inc_author in include_authors):
                    continue
            
            if exclude_authors:
                # Check if any of the exclude_authors is found in the author field (case-insensitive, partial match)
                if any(exc_author.lower() in author.lower() for exc_author in exclude_authors):
                    continue

            if not evaluation:
                state_groups['Not evaluated'].append(name)
            elif state == 'not installed':
                if evaluation == 'required':
                    state_groups['Required but not installed'].append(name)
                elif evaluation == 'desired':
                    state_groups['Desired but not installed'].append(name)
            elif state == 'installed':
                if evaluation == 'not desired':
                    state_groups['Not desired but installed'].append(name)
                elif evaluation == 'not required':
                    state_groups['Not required but installed'].append(name)
                elif evaluation == 'required':
                    required_and_migrated_count += 1

        # Print grouped results with better formatting and colors
        for state_name, modules in state_groups.items():
            if modules:  # Only print if there are modules in this state
                # Sort modules alphabetically
                modules.sort()
                
                # Color codes for different states
                if state_name == 'Not evaluated':
                    color = '\033[93m'  # Yellow
                elif state_name == 'Required but not installed':
                    color = '\033[91m'  # Red
                elif state_name == 'Desired but not installed':
                    color = '\033[94m'  # Blue
                elif state_name == 'Not desired but installed':
                    color = '\033[95m'  # Magenta
                elif state_name == 'Not required but installed':
                    color = '\033[96m'  # Cyan
                else:
                    color = '\033[0m'   # Default
                
                reset_color = '\033[0m'  # Reset color
                
                # Print status with module count on its own line with color
                module_count = len(modules)
                print(f"{color}{state_name}: {module_count} modules{reset_color}")
                
                # Print modules indented on the same line, separated by spaces
                modules_str = ' '.join(modules)
                print(f"  {modules_str}")
                print()  # Empty line for better separation

        if required_and_migrated_count > 0:
            color = '\033[92m'  # Green
            reset_color = '\033[0m'
            print(f"{color}Required and migrated modules:{reset_color}")
            print(f"  └─ {required_and_migrated_count} modules")

    except FileNotFoundError:
        print(f"Error: {yaml_file} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process CSV data and append to a YAML file.')
    subparsers = parser.add_subparsers(dest='command')

    # Subparser for --import-csv
    import_parser = subparsers.add_parser('import-csv')
    import_parser.add_argument('input_csv_file', help='Input CSV file')
    import_parser.add_argument('output_yaml_file', help='Output YAML file')
    import_parser.add_argument('odoo_version', help='Odoo version')

    # Subparser for --compare
    compare_parser = subparsers.add_parser('compare')
    compare_parser.add_argument('yaml_file', help='YAML file')
    compare_parser.add_argument('source_version', help='Source version')
    compare_parser.add_argument('target_version', help='Target version')

    # Subparser for --add-version
    add_version_parser = subparsers.add_parser('add-version')
    add_version_parser.add_argument('yaml_file', help='YAML file')
    add_version_parser.add_argument('odoo_version', help='Odoo version to add')

    # Subparser for --remove-version
    remove_version_parser = subparsers.add_parser('remove-version')
    remove_version_parser.add_argument('yaml_file', help='YAML file')
    remove_version_parser.add_argument('odoo_version', help='Odoo version to remove')

    # Subparser for --analyse
    analyse_parser = subparsers.add_parser('analyse')
    analyse_parser.add_argument('yaml_file', help='YAML file')
    analyse_parser.add_argument('odoo_version', help='Odoo version to analyse')
    analyse_parser.add_argument('--include-authors', nargs='+', help='Include only modules from these authors (space-separated list)')
    analyse_parser.add_argument('--exclude-authors', nargs='+', help='Exclude modules from these authors (space-separated list)')

    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(VERSION))

    args = parser.parse_args()

    if args.command == 'import-csv':
        process_csv(args.input_csv_file, args.output_yaml_file, args.odoo_version)
    elif args.command == 'compare':
        compare_versions(args.yaml_file, args.source_version, args.target_version)
    elif args.command == 'add-version':
        add_version(args.yaml_file, args.odoo_version)
    elif args.command == 'remove-version':
        remove_version(args.yaml_file, args.odoo_version)
    elif args.command == 'analyse':
        analyse(args.yaml_file, args.odoo_version, args.include_authors, args.exclude_authors)
    else:
        print("Please provide a valid command.")
