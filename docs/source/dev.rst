Developer Documentation
#######################

This document provides information for developers who want to contribute to the development of ``ucc``, as well as for maintainers.

Cutting a release
=================

.. important::
    This section is intended for maintainers of the :code:`ucc` repository.

To release a new version of ``ucc`` on GitHub, follow the steps below.

1. **Bump the Version:**
    - Increment the version in ``VERSION.txt`` according to `semantic versioning <https://semver.org/>`_.

2. **Update the Changelog:**
    - Update the ``CHANGELOG.rst`` file with all new changes, improvements, and bug fixes since the previous release.

3. **Commit Changes:**
    - Commit the changes to `VERSION.txt` and `CHANGELOG.rst` and open a PR to get the changes reviewed.

4. **Create a New Tag:**
    - Once the PR is merged, pull the changes to your local repository.
    - Create a new Git tag for the release. The tag name should match the version number (e.g., ``v1.1.0``).
    
    .. code-block:: bash

        git tag v1.1.0
        git push origin v1.1.0

5. **Draft a New Release on GitHub:**
    - Navigate to https://github.com/unitaryfund/ucc/releases to create a new release.
    - Select the newly created tag.
    - Fill in the release title and description, and copy the changelog entry for the description.
    - Publish the release.

.. tip::
    Ensure that all changes pass the tests, and the documentation builds correctly before creating a release.