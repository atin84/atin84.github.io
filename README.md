# QuickIris public website source

This repository hosts the public website [QuickIris](https://atin84.github.io/). It contains publicly served content, static site assets, the site generator, and deployment-related code.

## Public URLs
- Website: https://atin84.github.io/
- Related publishing site: https://quickiris.blogspot.com/

## Build and test

```sh
python3 -m unittest discover -s tests -v
python3 build.py --config config.json --content content --out dist
```

Publication to Blogger requires separate authorization. Do not commit API keys, tokens, credentials, or private business information.

Internal business strategy, AI operating instructions, expansion plans, editorial policy, and task tracking are intentionally **not stored in this public repository**.
