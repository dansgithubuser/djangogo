import os
import sys

DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(DIR, 'deps'))

import djangogo

parser = djangogo.make_parser()
args = parser.parse_args()
djangogo.main(args,
    project={project},
    app={app},
    db_name={db_name},
    db_user={db_user},
    heroku_url={heroku_url},
    heroku_repo={heroku_repo},
)
