// Football Match Hub - Jenkins CI/CD pipeline (SIT223/SIT753 Task 7.3HD)
// Stages so far: Build -> Test -> Code Quality -> Security. Deploy, Release and Monitoring are added next.

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
        // Python 3.13 (from Anaconda on this Mac). The macOS system Python 3.9 is too old for
        // current FastAPI and security tools. Each build creates its own clean venv from it.
        PYTHON = '/opt/anaconda3/bin/python3.13'
        // SonarScanner CLI (includes its own Java runtime) for the Code Quality stage.
        SCANNER_VERSION  = '7.3.0.5189'
        SCANNER_PLATFORM = 'macosx-aarch64'
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
                    ${PYTHON} -m venv --clear .venv
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

        stage('Code Quality') {
            steps {
                // SonarCloud analyses bugs, code smells, duplication and test coverage.
                // sonar.qualitygate.wait=true (sonar-project.properties) makes the scanner wait for the
                // Quality Gate and return an error if it fails, which stops the pipeline here.
                withCredentials([string(credentialsId: 'SONAR_TOKEN', variable: 'SONAR_TOKEN')]) {
                    sh '''
                        SCANNER_DIR="sonar-scanner-${SCANNER_VERSION}-${SCANNER_PLATFORM}"
                        if [ ! -x "$SCANNER_DIR/bin/sonar-scanner" ]; then
                            curl -sSLo scanner.zip "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SCANNER_VERSION}-${SCANNER_PLATFORM}.zip"
                            unzip -q -o scanner.zip && rm -f scanner.zip
                        fi
                        "$SCANNER_DIR/bin/sonar-scanner" -Dsonar.token="$SONAR_TOKEN" -Dsonar.projectVersion="$VERSION"
                    '''
                }
            }
        }

        stage('Security') {
            steps {
                // Bandit, pip-audit, npm audit and Trivy with a security gate (thresholds in ci/security_scan.sh).
                sh 'bash ci/security_scan.sh'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/security/**', allowEmptyArchive: true
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
