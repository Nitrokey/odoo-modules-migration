#!/usr/bin/env python3

import unittest
import tempfile
import os
import sys
import yaml
import csv

# Add the parent directory to the path to import omm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import omm


class TestOMMImportCSV(unittest.TestCase):
    """Test cases for the CSV import functionality with focus on state management."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = os.path.join(self.temp_dir, 'test.csv')
        self.yaml_file = os.path.join(self.temp_dir, 'test.yaml')
        self.odoo_version = '12.0'

    def tearDown(self):
        """Clean up after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_csv_file(self, modules):
        """Helper method to create a CSV file with given modules."""
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['name', 'author', 'state', 'auto_install'])
            for module in modules:
                writer.writerow([
                    module['name'],
                    module['author'],
                    module['state'],
                    module['auto_install']
                ])

    def create_yaml_file(self, modules):
        """Helper method to create a YAML file with given modules."""
        with open(self.yaml_file, 'w') as f:
            yaml.dump(modules, f, default_flow_style=False, sort_keys=False)

    def read_yaml_file(self):
        """Helper method to read and return YAML file contents."""
        with open(self.yaml_file, 'r') as f:
            return yaml.safe_load(f)

    def test_missing_modules_set_to_not_installed(self):
        """Test that modules in YAML but not in CSV are set to 'not installed'."""
        # Create initial YAML with modules
        initial_yaml = [
            {
                'name': 'module_in_both',
                'author': 'Test Author',
                self.odoo_version: {
                    'state': 'installed',
                    'auto_install': 'f',
                    'evaluation': 'required',
                    'comment': 'Important module'
                }
            },
            {
                'name': 'module_only_in_yaml',
                'author': 'Another Author',
                self.odoo_version: {
                    'state': 'installed',
                    'auto_install': 'f',
                    'evaluation': 'desired',
                    'comment': 'Will be missing from CSV'
                }
            },
            {
                'name': 'another_missing_module',
                'author': 'Third Author',
                self.odoo_version: {
                    'state': 'installed',
                    'auto_install': 't',
                    'evaluation': 'not required',
                    'comment': 'Also missing from CSV'
                }
            }
        ]
        self.create_yaml_file(initial_yaml)

        # Create CSV with only some modules
        csv_modules = [
            {
                'name': 'module_in_both',
                'author': 'Test Author',
                'state': 'installed',
                'auto_install': 'f'
            },
            {
                'name': 'new_module_from_csv',
                'author': 'CSV Author',
                'state': 'installed',
                'auto_install': 'f'
            }
        ]
        self.create_csv_file(csv_modules)

        # Process CSV
        omm.process_csv(self.csv_file, self.yaml_file, self.odoo_version)

        # Read result
        result = self.read_yaml_file()

        # Verify results
        self.assertEqual(len(result), 4)  # 3 original + 1 new

        # Find modules in result
        modules_by_name = {module['name']: module for module in result}

        # Module present in both should remain installed
        module_in_both = modules_by_name['module_in_both']
        self.assertEqual(module_in_both[self.odoo_version]['state'], 'installed')
        self.assertEqual(module_in_both[self.odoo_version]['evaluation'], 'required')
        self.assertEqual(module_in_both[self.odoo_version]['comment'], 'Important module')

        # Modules only in YAML should be set to 'not installed'
        module_only_in_yaml = modules_by_name['module_only_in_yaml']
        self.assertEqual(module_only_in_yaml[self.odoo_version]['state'], 'not installed')
        self.assertEqual(module_only_in_yaml[self.odoo_version]['evaluation'], 'desired')
        self.assertEqual(module_only_in_yaml[self.odoo_version]['comment'], 'Will be missing from CSV')

        another_missing = modules_by_name['another_missing_module']
        self.assertEqual(another_missing[self.odoo_version]['state'], 'not installed')
        self.assertEqual(another_missing[self.odoo_version]['evaluation'], 'not required')
        self.assertEqual(another_missing[self.odoo_version]['comment'], 'Also missing from CSV')

        # New module from CSV should be added
        new_module = modules_by_name['new_module_from_csv']
        self.assertEqual(new_module[self.odoo_version]['state'], 'installed')
        self.assertEqual(new_module['author'], 'CSV Author')

    def test_empty_yaml_file(self):
        """Test importing CSV into an empty YAML file."""
        # Create empty YAML file
        self.create_yaml_file([])

        # Create CSV with modules
        csv_modules = [
            {
                'name': 'new_module',
                'author': 'Test Author',
                'state': 'installed',
                'auto_install': 'f'
            }
        ]
        self.create_csv_file(csv_modules)

        # Process CSV
        omm.process_csv(self.csv_file, self.yaml_file, self.odoo_version)

        # Read result
        result = self.read_yaml_file()

        # Verify results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'new_module')
        self.assertEqual(result[0][self.odoo_version]['state'], 'installed')

    def test_nonexistent_yaml_file(self):
        """Test importing CSV when YAML file doesn't exist."""
        # Don't create YAML file
        
        # Create CSV with modules
        csv_modules = [
            {
                'name': 'new_module',
                'author': 'Test Author',
                'state': 'installed',
                'auto_install': 'f'
            }
        ]
        self.create_csv_file(csv_modules)

        # Process CSV
        omm.process_csv(self.csv_file, self.yaml_file, self.odoo_version)

        # Verify YAML file was created
        self.assertTrue(os.path.exists(self.yaml_file))

        # Read result
        result = self.read_yaml_file()

        # Verify results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'new_module')
        self.assertEqual(result[0][self.odoo_version]['state'], 'installed')

    def test_preserve_evaluation_and_comments(self):
        """Test that evaluation and comment fields are preserved during import."""
        # Create initial YAML with evaluation and comments
        initial_yaml = [
            {
                'name': 'test_module',
                'author': 'Test Author',
                self.odoo_version: {
                    'state': 'not installed',
                    'auto_install': 'f',
                    'evaluation': 'required',
                    'comment': 'Critical for business'
                }
            }
        ]
        self.create_yaml_file(initial_yaml)

        # Create CSV with same module but different state
        csv_modules = [
            {
                'name': 'test_module',
                'author': 'Test Author',
                'state': 'installed',
                'auto_install': 'f'
            }
        ]
        self.create_csv_file(csv_modules)

        # Process CSV
        omm.process_csv(self.csv_file, self.yaml_file, self.odoo_version)

        # Read result
        result = self.read_yaml_file()

        # Verify evaluation and comment are preserved
        module = result[0]
        self.assertEqual(module[self.odoo_version]['state'], 'installed')  # Updated from CSV
        self.assertEqual(module[self.odoo_version]['evaluation'], 'required')  # Preserved
        self.assertEqual(module[self.odoo_version]['comment'], 'Critical for business')  # Preserved

    def test_multiple_versions(self):
        """Test that the fix works correctly with multiple Odoo versions."""
        # Create initial YAML with multiple versions
        initial_yaml = [
            {
                'name': 'multi_version_module',
                'author': 'Test Author',
                '11.0': {
                    'state': 'installed',
                    'auto_install': 'f',
                    'evaluation': 'required',
                    'comment': 'Old version'
                },
                self.odoo_version: {
                    'state': 'installed',
                    'auto_install': 'f',
                    'evaluation': 'required',
                    'comment': 'Current version'
                }
            }
        ]
        self.create_yaml_file(initial_yaml)

        # Create CSV that doesn't include this module
        csv_modules = [
            {
                'name': 'different_module',
                'author': 'Other Author',
                'state': 'installed',
                'auto_install': 'f'
            }
        ]
        self.create_csv_file(csv_modules)

        # Process CSV for version 12.0
        omm.process_csv(self.csv_file, self.yaml_file, self.odoo_version)

        # Read result
        result = self.read_yaml_file()

        # Find the multi-version module
        multi_version_module = next(m for m in result if m['name'] == 'multi_version_module')

        # Verify that only the target version was updated
        self.assertEqual(multi_version_module['11.0']['state'], 'installed')  # Unchanged
        self.assertEqual(multi_version_module[self.odoo_version]['state'], 'not installed')  # Updated

    def test_version_key_consistency(self):
        """Test that version keys are handled consistently (string vs numeric)."""
        # Create YAML with numeric version key (as YAML might parse it)
        initial_yaml = [
            {
                'name': 'version_test_module',
                'author': 'Test Author',
                12.0: {  # Numeric key
                    'state': 'installed',
                    'auto_install': 'f',
                    'evaluation': 'required',
                    'comment': 'Test comment'
                }
            }
        ]
        self.create_yaml_file(initial_yaml)

        # Create CSV without this module
        csv_modules = [
            {
                'name': 'other_module',
                'author': 'Other Author',
                'state': 'installed',
                'auto_install': 'f'
            }
        ]
        self.create_csv_file(csv_modules)

        # Process CSV with string version
        omm.process_csv(self.csv_file, self.yaml_file, '12.0')

        # Read result
        result = self.read_yaml_file()

        # Find the test module
        test_module = next(m for m in result if m['name'] == 'version_test_module')

        # Verify that the state was updated regardless of key type
        version_data = None
        for key, value in test_module.items():
            if str(key) == '12.0' and isinstance(value, dict):
                version_data = value
                break

        self.assertIsNotNone(version_data)
        self.assertEqual(version_data['state'], 'not installed')
        self.assertEqual(version_data['evaluation'], 'required')
        self.assertEqual(version_data['comment'], 'Test comment')


class TestOMMAnalyse(unittest.TestCase):
    """Test cases for the analyse functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.yaml_file = os.path.join(self.temp_dir, 'test.yaml')
        self.odoo_version = '12.0'

    def tearDown(self):
        """Clean up after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_yaml_file(self, modules):
        """Helper method to create a YAML file with given modules."""
        with open(self.yaml_file, 'w') as f:
            yaml.dump(modules, f, default_flow_style=False, sort_keys=False)

    def test_analyse_with_not_installed_modules(self):
        """Test that analyse correctly categorizes modules with 'not installed' state."""
        # Create YAML with various module states including 'not installed'
        test_yaml = [
            {
                'name': 'required_not_installed',
                'author': 'Test Author',
                self.odoo_version: {
                    'state': 'not installed',
                    'auto_install': 'f',
                    'evaluation': 'required',
                    'comment': 'Should be in required but not installed'
                }
            },
            {
                'name': 'desired_not_installed',
                'author': 'Test Author',
                self.odoo_version: {
                    'state': 'not installed',
                    'auto_install': 'f',
                    'evaluation': 'desired',
                    'comment': 'Should be in desired but not installed'
                }
            },
            {
                'name': 'installed_required',
                'author': 'Test Author',
                self.odoo_version: {
                    'state': 'installed',
                    'auto_install': 'f',
                    'evaluation': 'required',
                    'comment': 'Should be counted as migrated'
                }
            }
        ]
        self.create_yaml_file(test_yaml)

        # Capture output by redirecting stdout
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            omm.analyse(self.yaml_file, self.odoo_version)

        output = captured_output.getvalue()

        # Verify that the analysis correctly categorizes modules
        self.assertIn('Required but not installed: 1 modules', output)
        self.assertIn('required_not_installed', output)
        self.assertIn('Desired but not installed: 1 modules', output)
        self.assertIn('desired_not_installed', output)
        self.assertIn('Required and migrated modules:', output)
        self.assertIn('1 modules', output)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
