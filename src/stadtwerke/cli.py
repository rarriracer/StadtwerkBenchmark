import argparse
import json
import uuid
from .workflow import invoke

def main():
    parser = argparse.ArgumentParser(description='Stadtwerke-Ausblick mit lokalem Modell')
    parser.add_argument('pdf')
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--company', default='')
    parser.add_argument('--max-pages', type=int, default=None, help='Optionales Seitenlimit für einen schnellen Test; standardmäßig ohne Limit')
    parser.add_argument('--target-year', type=int, default=2026)
    parser.add_argument('--topics', nargs='*')
    args = parser.parse_args()
    session = str(uuid.uuid4())
    state = invoke(session, initial={'path': args.pdf, 'year': args.year, 'company': args.company, 'max_pages': args.max_pages})
    print('Session:', session, flush=True)
    if state.get('__interrupt__'):
        options = state['__interrupt__'][0].value['options']
        print('Auswahl:', list(options), flush=True)
        if args.topics:
            state = invoke(session, selection={'metrics': args.topics, 'target_year': args.target_year, 'spread': 0})
    print(json.dumps({'files': state.get('files'), 'status': state.get('status'),
                      'errors': state.get('report', {}).get('metadata', {}).get('extraction_errors')}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
