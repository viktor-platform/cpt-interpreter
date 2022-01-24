# Publishing a Sample App

1. Create the Sample App with a specific 'Theme' or 'Topic'
2. Check code style, formatting, type-hints, etc. (pylint will help with this)
   1. Doc-strings for every module, class and function
   2. Type-hints wherever possible
   3. Don't use overly complicated code structures / syntax
   4. Try to keep it compact, (Parametrization lines are allowed to surpass the 120 char line length)
   5. Try to avoid external dependencies as much as possible
3. Write a comprehensive README following the standard format:
   1. Update the SDK version badge at the top of README (if necessary)
   2. Update title and description
   3. Update App structure section (only if app has more than 2 entity types)
4. Update the background image to be relevant to the sample app (be wary of copy-right)
5. Update the 'release date' of v1.0.0 inside the CHANGELOG.md
6. Publish the sample app repo on github, using `sample-APP-NAME`. Do not include the following files:
   - `.gitignore`
   - `.gitlab-ci.yml`
   - `.pylintrc`
   - `CONTRIBUTING.md`
7. Update the 'Repository details' ('About') or the new sample app repo:
   1. Description: the first introductory line of the README
   2. Topics: add (at least) 'example' and 'viktor-ai'