// Football Match Hub - Jenkins CI/CD pipeline (SIT223/SIT753 Task 7.3HD)
// Stages so far: Build -> Test. Code Quality, Security, Deploy, Release and Monitoring are added next.

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    // GitHub webhooks cannot reach a laptop, so Jenkins checks the repo for new commits every 5 minutes.
    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        // Jenkins runs as a Homebrew service and does not inherit the shell PATH:
        // /opt/homebrew/bin has node/npm, /usr/local/bin has docker (Docker Desktop).
        PATH = "/opt/homebrew/bin:/usr/local/bin:${env.PATH}"
        BACKEND_IMAGE  = 'fmh-backend'
        FRONTEND_IMAGE = 'fmh-frontend'
        // Tests and CI never call the paid API.
        USE_MOCK = 'true'
    }

    stages {
        stage('Build') {
            steps {
                script {
                    // Version = 1.0.<build number>, image tag also includes the commit for traceability.
                    env.GIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.VERSION   = "1.0.${env.BUILD_NUMBER}"
                    env.IMAGE_TAG = "${env.VERSION}-${env.GIT_SHORT}"
                }
                echo "Building version ${env.IMAGE_TAG}"

                // Backend: isolated virtual environment with app + test dependencies.
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    python -m pip install -q --upgrade pip
                    python -m pip install -q -r backend/requirements-dev.txt
                '''

                // Frontend: clean install from the lock file, then a production build.
                dir('frontend') {
                    sh 'npm ci --no-audit --no-fund'
                    sh 'npm run build'
                }

                // Docker images are the deployable build artifacts, tagged with version + commit.
                sh '''
                    docker build -t ${BACKEND_IMAGE}:${IMAGE_TAG}  -t ${BACKEND_IMAGE}:latest  backend
                    docker build -t ${FRONTEND_IMAGE}:${IMAGE_TAG} -t ${FRONTEND_IMAGE}:latest frontend
                    docker image ls --filter reference='fmh-*'
                '''
            }
            post {
                success {
                    archiveArtifacts artifacts: 'frontend/dist/**', fingerprint: true
                }
            }
        }

        stage('Test') {
            steps {
                // Backend: unit + integration tests (pytest), with coverage for SonarCloud.
                sh '''
                    . .venv/bin/activate
                    cd backend
                    python -m pytest --junitxml=reports/junit.xml --cov --cov-report=xml:coverage.xml --cov-report=term
                '''
                // Frontend: unit tests (Vitest), with lcov coverage.
                dir('frontend') {
                    sh 'npm run test:coverage'
                }
            }
            post {
                always {
                    // Publish results in Jenkins; any failed test marks the build as failed and stops the pipeline.
                    junit testResults: 'backend/reports/junit.xml, frontend/reports/junit.xml'
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded for ${env.IMAGE_TAG}"
        }
        failure {
            echo 'Pipeline failed - check the stage that is marked red.'
        }
    }
}
