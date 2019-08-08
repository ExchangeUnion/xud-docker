xud-docker
==========
A 0-install [xud](https://github.com/ExchangeUnion/xud) environment using [docker](https://www.docker.com/)

Description and usage:
* [xud wiki](https://github.com/ExchangeUnion/xud/wiki/Docker)

### Developing
The following chapter is meant for developers.

#### Initial setup
`git clone https://github.com/ExchangeUnion/xud-docker.git ~/xud-docker`

Init and fetch git submodules
`git submodule init`
`git submodule update --recursive --remote`

#### Developing a feature
Create a feature branch
`git checkout -b your-feature-branch`

Make your desired changes to the images located at:
`~/xud-docker/images`

Build the updated image(s)
`~/xud-docker/tools/build image_name`

Tag the image with local suffix:
`docker tag image_name image_name__local`

Change `docker-compose.yml` to use the updated image tag. Commit and push the changes.

Start the Docker environment using your feature branch:
- `bash ~/xud.sh -b your-feature-branch`

#### Workflow
1. Change the image and rebuild it
2. docker-compose down
3. docker-compose up -d
