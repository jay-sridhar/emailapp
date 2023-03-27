import argparse
import os.path
import json

from businesslogic.rules_processor import RulesProcessor


class VerifyAndSetPathAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not os.path.exists(values[0]) or values[0].endswith("/"):
            raise ValueError("Please provide a valid file path")
        try:
            with open(values[0], "r") as file_obj:
                rules = json.load(file_obj)
                setattr(namespace, self.dest, rules)
                print(f"\n\nINPUT RULE:\n\n{json.dumps(rules, indent=4)}")
        except Exception:
            raise ValueError("Please provide a file containing a valid JSON rule")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='This script runs the rules present in emailapp/resources/rules.json file '
                    'on the emails stored in the database and applies them to your Gmail account. ',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-r', nargs=1, metavar='rules_file_path', required=True,
                        help='Specify an absolute or relative path to an alternate .json file that contains '
                             'rules in the same format as emailapp/resources/rules.json', action=VerifyAndSetPathAction)
    args = parser.parse_args()
    RulesProcessor().process_rules(args.r)
