"""Create the managed access history dataset explicitly from a DSS runtime."""
import argparse
from .repositories.dss import DSSRepository


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection', required=True, help='Existing DSS connection enabled for managed datasets')
    args = parser.parse_args()
    result = DSSRepository().provision_access_history(args.connection)
    print(('Created' if result['created'] else 'Validated existing') + ' managed dataset: ' + result['dataset'])


if __name__ == '__main__':
    main()
