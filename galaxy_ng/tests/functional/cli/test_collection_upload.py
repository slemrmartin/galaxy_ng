"""Tests that Collections can be uploaded to Pulp with the ansible-galaxy CLI."""

import subprocess
import tempfile
from unittest.case import skip

from pulp_smash.pulp3.bindings import delete_orphans
from pulp_smash.utils import http_get

from galaxy_ng.tests.functional.utils import TestCaseUsingBindings
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class UploadCollectionTestCase(TestCaseUsingBindings):
    """Test whether ansible-galaxy can upload a Collection to Pulp."""

    def test_upload_collection(self):
        """Test whether ansible-galaxy can upload a Collection to Pulp."""
        delete_orphans()

        # Create namespace if it doesn't exist
        data = str(self.namespace_api.list().data)
        if "pulp" not in data:
            self.namespace_api.create(namespace={"name": "pulp", "groups": []})

        # Preapare ansible.cfg for ansible-galaxy CLI
        self.update_ansible_cfg("inbound-pulp")

        # In a temp dir, publish a collection using ansible-galaxy CLI
        with tempfile.TemporaryDirectory() as tmp_dir:
            content = http_get("https://galaxy.ansible.com/download/pulp-squeezer-0.0.9.tar.gz")
            collection_path = f"{tmp_dir}/pulp-squeezer-0.0.9.tar.gz"
            with open(collection_path, "wb") as f:
                f.write(content)

            cmd = "ansible-galaxy collection publish -vvv -c {}".format(collection_path)

            subprocess.run(cmd.split())

        # Verify that the collection was published
        collections = self.collections_api.list("published")
        self.assertEqual(collections.meta.count, 1)

        collection = self.collections_api.read(path="published", namespace="pulp", name="squeezer")
        self.assertEqual(collection.namespace, "pulp")
        self.assertEqual(collection.name, "squeezer")
        self.assertEqual(collection.highest_version["version"], "0.0.9")

        # Cleanup
        self.delete_collection(collection.namespace, collection.name)
        self.delete_namespace(collection.namespace)

    def test_uploaded_collection_logged(self):
        """Test whether a Collection uploaded via ansible-galaxy is logged correctly in API Access Log."""
        delete_orphans()

        # Create namespace if it doesn't exist
        data = str(self.namespace_api.list().data)
        if "pulp" not in data:
            self.namespace_api.create(namespace={"name": "pulp", "groups": []})

        # Preapare ansible.cfg for ansible-galaxy CLI
        self.update_ansible_cfg("inbound-pulp")

        # In a temp dir, publish a collection using ansible-galaxy CLI
        with tempfile.TemporaryDirectory() as tmp_dir:
            content = http_get("https://galaxy.ansible.com/download/pulp-squeezer-0.0.9.tar.gz")
            collection_path = f"{tmp_dir}/pulp-squeezer-0.0.9.tar.gz"
            with open(collection_path, "wb") as f:
                f.write(content)

            cmd = "ansible-galaxy collection publish -vvv -c {}".format(collection_path)

            subprocess.run(cmd.split())

            cmd = f"docker cp pulp:/var/log/galaxy_api_access.log {tmp_dir}"

            subprocess.run(cmd.split())

            with open(f"{tmp_dir}/galaxy_api_access.log") as f:
                log_contents = f.readlines()
                print(log_contents)

        # Verify that the collection was published
        collections = self.collections_api.list("published")
        self.assertEqual(collections.meta.count, 1)

        # Verify that the colletion publishing was logged in the api access log
        collection = self.collections_api.read(path="published", namespace="pulp", name="squeezer")
        for line in log_contents:
            if "INFO: Collection uploaded by user 'admin': " in line and 'pulp' in line:
                self.assertIn(collection.namespace, line)
                self.assertIn(collection.name, line)
                self.assertIn(collection.highest_version["version"], line)

        # Cleanup
        self.delete_collection(collection.namespace, collection.name)
        self.delete_namespace(collection.namespace)
