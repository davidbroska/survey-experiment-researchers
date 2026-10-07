The dedicated repository is [davidbroska/survey-experiment-researchers](https://github.com/davidbroska/survey-experiment-researchers). It contains only the recruitment project, with this folder’s contents at the repository root. PDFs, extracted text, Scopus caches, credentials, and unrelated SocialTune files are excluded.

The workflow in `.github/workflows/pages.yml` runs the unit checks, stages the allowlisted `site/` directory, checks its internal links, and deploys that directory through GitHub Pages. The publishing source is **GitHub Actions**. [GitHub workflow instructions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

For an update, complete the local review, rebuild the reports and site, then commit the public recruitment files and push `main`. The existing private snapshot is required for rebuilding the research dashboard; the public workflow deploys the already-generated research outputs and needs no Scopus credentials or PDFs. Check the Actions result and [dashboard URL](https://davidbroska.github.io/survey-experiment-researchers/).

Local rebuild commands:

```bash
python3 pipeline/fulltext.py
python3 pipeline/run.py reports
python3 pipeline/compare_years.py
python3 pipeline/build_site.py
python3 -m unittest discover -s tests -v
```

The ZIP is an alternative upload bundle containing only the generated site. Keep the research source folders in the repository so the method, query, and update code remain reviewable.
