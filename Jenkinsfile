// evaluator-repo/Jenkinsfile

pipeline {
    agent {
        docker {
            image 'python:3.12-slim'
            args "-v /var/run/docker.sock:/var/run/docker.sock --group-add ${env.DOCKER_GID}"
        }
    }

    parameters {
        string(name: 'HARBOR_CREDENTIALS_ID', defaultValue: 'harbor-credentials', description: 'The ID of your Harbor credentials in Jenkins')
    }

    environment {
        HARBOR_URL = "harbor.${env.DOMAIN}"
        IMAGE_NAME = "${HARBOR_URL}/evalify/evaluator"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    def branchName = env.BRANCH_NAME.replaceAll('/', '-')
                    env.IMAGE_TAG = env.TAG_NAME ?: "${branchName}-${env.BUILD_NUMBER}"
                }
            }
        }

        stage('Build & Push Docker Image') {
            when {
                anyOf {
                    branch 'release'
                    branch 'master'
                }
            }
            steps {
                script {
                    echo "Building Evaluator Image: ${IMAGE_NAME}:${IMAGE_TAG}"
                    def customImage = docker.build(
                        "${IMAGE_NAME}:${IMAGE_TAG}",
                        "-f Dockerfile ."
                    )
                    docker.withRegistry("https://${HARBOR_URL}", 'harbor-credentials') {
                        customImage.push()
                        customImage.push('latest')
                    }
                }
            }
        }

        stage('Trigger Deploy') {
            when {
                anyOf {
                    branch 'release'
                    branch 'master'
                }
            }
            steps {
                echo "Deploying evaluator version: ${IMAGE_TAG}"
                build job: 'Deployer_Pipeline', parameters: [
                    booleanParam(name: 'DEPLOY_EVALUATOR', value: true),
                    string(name: 'EVALUATOR_IMAGE_URL', value: "${IMAGE_NAME}:${IMAGE_TAG}")
                ]
            }
        }
    }
}
