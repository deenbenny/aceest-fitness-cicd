
pipeline {
    agent any

    environment {
        SONAR_PROJECT = 'aceest-fitness-cicd'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup & Lint') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    pip install pytest flake8

                    flake8 . --exclude=venv,legacy \
                        --select=E9,F63,F7,F82

                    python -m py_compile app.py
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    python -m pytest -v
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('ACEest-SonarQube') {
                    withCredentials([
                        string(
                            credentialsId: 'sonar-token',
                            variable: 'SONAR_TOKEN'
                        )
                    ]) {
                        sh '''
                            docker run --rm \
                                --network aceest-network \
                                -e SONAR_HOST_URL="$SONAR_HOST_URL" \
                                -e SONAR_TOKEN="$SONAR_TOKEN" \
                                -v "$WORKSPACE:/usr/src" \
                                sonarsource/sonar-scanner-cli \
                                -Dsonar.projectBaseDir=/usr/src
                        '''
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build \
                        -t deenbenny/aceest-fitness:v3.2.7 \
                        -t deenbenny/aceest-fitness:latest \
                        .
                '''
            }
        }

        stage('Push Docker Image') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login \
                            -u "$DOCKER_USER" --password-stdin

                        docker push $DOCKER_USER/aceest-fitness:v3.2.7
                        docker push $DOCKER_USER/aceest-fitness:latest

                        docker logout
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}

