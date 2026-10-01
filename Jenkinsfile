// Football Match Hub - Jenkins CI/CD pipeline (SIT223/SIT753 Task 7.3HD)
// Build -> Test -> Code Quality -> Security -> Deploy (staging) -> Release (production) -> Monitoring

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

    parameters {
        booleanParam(name: 'SIMULATE_BAD_RELEASE', defaultValue: false,
            description: 'Demo only: release with a broken configuration to show the automatic rollback.')
    }

    environment {
        // Jenkins runs as a Homebrew service and does not inherit the shell PATH:
        // /opt/homebrew/bin has node/npm, /usr/local/bin has docker (Docker Desktop).
        PATH = "/opt/homebrew/bin:/usr/local/bin:${env.PATH}"
        BACKEND_IMAGE  = 'fmh-backend'
        FRONTEND_IMAGE = 'fmh-frontend'
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

        stage('Deploy') {
            steps {
                // STAGING environment (mock data) from deploy/docker-compose.yml + deploy/staging.env,
                // running exactly the images built in this pipeline run (IMAGE_TAG).
                sh '''
                    docker network inspect fmh-monitoring > /dev/null 2>&1 || docker network create fmh-monitoring
                    docker compose -p fmh-staging --env-file deploy/staging.env -f deploy/docker-compose.yml up -d --remove-orphans
                    bash ci/smoke_test.sh http://localhost:8081 http://localhost:8001 "$IMAGE_TAG" true
                '''
            }
            post {
                failure {
                    sh 'docker compose -p fmh-staging --env-file deploy/staging.env -f deploy/docker-compose.yml logs --tail=50 || true'
                }
            }
        }

        stage('Release') {
            steps {
                // Manual approval gate: a person promotes the tested build to production.
                timeout(time: 15, unit: 'MINUTES') {
                    input message: "Staging passed. Release ${env.IMAGE_TAG} to PRODUCTION?", ok: 'Release'
                }
                // Production uses the real API key from Jenkins Credentials (masked in the log, never in Git).
                // ci/release.sh smoke-tests production and rolls back automatically if it fails.
                withCredentials([string(credentialsId: 'API_FOOTBALL_KEY', variable: 'API_FOOTBALL_KEY')]) {
                    sh 'SIMULATE_BAD_RELEASE=${SIMULATE_BAD_RELEASE} bash ci/release.sh'
                }
                // Version the release in Git: tag v1.0.<build> on the released commit and push it to GitHub.
                withCredentials([usernamePassword(credentialsId: 'github-token',
                                                  usernameVariable: 'GH_USER', passwordVariable: 'GH_TOKEN')]) {
                    sh '''
                        git -c user.name="Jenkins" -c user.email="jenkins@localhost" \
                            tag -a "v${VERSION}" -m "Release v${VERSION} (images ${IMAGE_TAG})"
                        git push "https://${GH_USER}:${GH_TOKEN}@github.com/hieunguyenduc46-lgtm/football-match-hub.git" "v${VERSION}"
                    '''
                }
            }
        }

        stage('Monitoring') {
            steps {
                // Prometheus + Alertmanager + Grafana; the script checks production is scraped and alerts are loaded.
                sh 'bash ci/monitoring.sh'
            }
        }
    }

    post {
        success {
            echo "Released ${env.IMAGE_TAG}: production http://localhost:8088 | staging http://localhost:8081 | Grafana http://localhost:3000"
        }
        failure {
            echo 'Pipeline failed - check the stage that is marked red.'
        }
    }
}
