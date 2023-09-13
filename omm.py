import argparse
import csv
import sys
import yaml
import re
import os

# Define the version number
VERSION = '0.1'


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

        for name, new_data in data_dict.items():
            index = next((i for i, item in enumerate(existing_data) if item['name'] == name), None)
            if index is not None:
                new_data[odoo_version]["evaluation"] = existing_data[index].get(odoo_version, {}).get("evaluation", "")
                new_data[odoo_version]["comment"] = existing_data[index].get(odoo_version, {}).get("comment", "")
                existing_data[index].setdefault(odoo_version, {}).update(new_data[odoo_version])
            else:
                existing_data.append(new_data)

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

        with open(yaml_file_path, 'w') as yaml_file:
            yaml.dump(data, yaml_file, default_flow_style=False, sort_keys=False, width=float('inf'))

        print(f"Removed version '{odoo_version}' from all entries in '{yaml_file_path}'.")
    except Exception as e:
        print(f"An error occurred: {e}")


def analyse(yaml_file, odoo_version):
    try:
        with open(yaml_file, 'r') as existing_yaml_file:
            existing_data = yaml.safe_load(existing_yaml_file)
            if existing_data is None:
                existing_data = []

        required_and_migrated_count = 0

        for entry in existing_data:
            entry_data = entry.get(odoo_version, {})
            state = entry_data.get('state', '')
            evaluation = entry_data.get('evaluation', '')
            name = entry.get('name', '')

            if not evaluation:
                print(f"Not evaluated: {name}")
            elif state == 'not installed':
                if evaluation == 'required':
                    print(f"Required but not installed: {name}")
                elif evaluation == 'desired':
                    print(f"Desired but not installed: {name}")
            elif state == 'installed':
                if evaluation == 'not desired':
                    print(f"Not desired but installed: {name}")
                elif evaluation == 'not required':
                    print(f"Not required but installed: {name}")
                elif evaluation == 'required':
                    required_and_migrated_count += 1

        if required_and_migrated_count > 0:
            print(f"Required and migrated modules: {required_and_migrated_count}")

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
    remove_version_parser = subparsers.add_parser('analyse')
    remove_version_parser.add_argument('yaml_file', help='YAML file')
    remove_version_parser.add_argument('odoo_version', help='Odoo version to analyse')

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
        analyse(args.yaml_file, args.odoo_version)
    else:
        print("Please provide a valid command.")
