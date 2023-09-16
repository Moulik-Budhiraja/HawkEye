'''This module provides versioning utilities'''


class SemanticVersion:
    '''Basic semantic versioning functionality
    Increment:
    - MAJOR version when you make incompatible API changes, Reset MINOR and PATCH to 0
    - MINOR version when you add functionality in a backwards compatible manner, Reset PATCH to 0
    - PATCH version when you make a backwards compatible bug fix
    Additional labels for pre-release and build metadata are available as extensions to the MAJOR.MINOR.PATCH format.
    '''

    def __init__(self, major, minor, patch, metadata=None):
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)
        self.metadata = metadata

    def check_compatibility(self, dependency):
        '''Returns true if this version is compatible with the version of the dependency'''
        return self.major == dependency.major and self.minor <= dependency.minor

    def __str__(self):
        return f'{self.major}.{self.minor}.{self.patch}' + \
            (f'-{self.metadata}' if self.metadata else '')

    @staticmethod
    def from_string(version: str):
        ''' Create a semantic version from string '''
        return SemanticVersion(*version.split(sep='.'))

    # pylint: disable=too-many-return-statements
    @staticmethod
    def compare(ver1, ver2):
        '''The return value is negative if ver1 < ver2, zero if ver1 == ver2 and strictly positive if ver1 > ver2'''
        if ver1.major < ver2.major:
            return -1
        if ver1.major > ver2.major:
            return 1

        if ver1.minor < ver2.minor:
            return -1
        if ver1.minor > ver2.minor:
            return 1

        if ver1.patch < ver2.patch:
            return -1
        if ver1.patch > ver2.patch:
            return 1

        return 0
