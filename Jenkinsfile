pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Setup & Lint') {
            steps {
                sh '''
                  python3 -m venv venv
                  . venv/bin/activate
                  pip install -r requirements.txt
                  flake8 . --exclude=venv,legacy --select=E9,F63,F7,F82
                  python -m py_compile app.py
                '''
            }
        }
        stage('Unit Tests') {
            steps { sh '. venv/bin/activate && python -m pytest' }
        }
        stage('Docker Build') {
            steps { sh 'docker build -t aceest-fitness:${BUILD_NUMBER} .' }
        }
        stage('Test in Container') {
            steps { sh 'docker run --rm aceest-fitness:${BUILD_NUMBER} pytest' }
        }
    }
    post {
        always { cleanWs() }
    }
}
