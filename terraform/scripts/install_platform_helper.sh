## Build platform-helper
#echo -e "\n\n### Build and install platform-helper cloned from ${PLATFORM_HELPER_VERSION}\n" #TODO
echo -e "\n\n### Build and install platform-helper cloned from main\n"
echo -e "Installing dependencies"
pip install poetry
poetry install
echo -e "\nBuild platform-helper\n"
#poetry build --no-interaction --format sdist --no-ansi --local-version ${PLATFORM_HELPER_VERSION} #TODO
poetry build --no-interaction --format sdist --no-ansi --local-version main
echo -e "\nInstall platform-helper\n"
most_recent_built_wheel_package=$(ls -t1 dist | grep ".whl" | head -1)
pip install "dist/${most_recent_built_wheel_package}"
echo -e "\nCheck which platform-helper\n"
which platform-helper
echo -e "\nCheck platform-helper --version\n"
platform-helper --version
