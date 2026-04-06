pipeline {
    agent {
        kubernetes {
            cloud 'kubernetes'
            defaultContainer 'python'
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    jenkins/label: flask-app-build
spec:
  containers:
    - name: python
      image: python:3.12-slim
      command:
        - sleep
      args:
        - "9999999"
      tty: true
      workingDir: /home/jenkins/agent
      volumeMounts:
        - mountPath: /home/jenkins/.cache/pip
          name: pip-cache
    - name: docker
      image: docker:27-cli
      command:
        - sleep
      args:
        - "9999999"
      tty: true
      workingDir: /home/jenkins/agent
      volumeMounts:
        - mountPath: /var/run/docker.sock
          name: docker-sock
  volumes:
    - name: pip-cache
      emptyDir: {}
    - name: docker-sock
      hostPath:
        path: /var/run/docker.sock
'''
        }
    }

    parameters {
        string(name: 'IMAGE_NAME', defaultValue: 'kaiwenyao/flask-app', description: 'Docker image name')
        string(name: 'IMAGE_TAG', defaultValue: '', description: 'Image tag (empty means BUILD_NUMBER)')
        booleanParam(name: 'PUSH_IMAGE', defaultValue: true, description: 'Push image to registry')
        booleanParam(name: 'DEPLOY_TO_EC2', defaultValue: false, description: 'Deploy container to EC2')
        string(name: 'CONTAINER_NAME', defaultValue: 'flask-app', description: 'Container name on EC2')
        string(name: 'CONTAINER_ENV_FILE', defaultValue: '/opt/flask-app/.env', description: 'Env file path on EC2')
        string(name: 'EC2_SSH_KEY_CREDENTIALS_ID', defaultValue: 'server-ssh-key', description: 'Jenkins SSH key credential ID')
    }

    environment {
        DOCKER_CREDENTIALS_ID = 'docker-hub-credentials'
        SERVER_HOST_CREDENTIALS_ID = 'aws-ec2'
        ENV_FILE_CREDENTIALS_ID = 'flask-prod.env'
    }

    stages {
        stage('1. 拉取代码') {
            steps {
                checkout scm
            }
        }

        stage('2. Python 语法检查') {
            steps {
                container('python') {
                    sh '''
                    python --version
                    python -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    python -m py_compile config.py run.py wsgi.py $(find app -name '*.py')
                    '''
                }
            }
        }

        stage('3. 执行测试') {
            steps {
                container('python') {
                    sh '''
                    . .venv/bin/activate
                    pip install pytest pytest-cov
                    mkdir -p test-reports
                    pytest tests/ --junitxml=test-reports/pytest.xml
                    '''
                }
            }
            post {
                always {
                    junit testResults: 'test-reports/pytest.xml', allowEmptyResults: false
                }
            }
        }

        stage('4. 下载 ML 模型') {
            steps {
                container('python') {
                    withCredentials([
                        string(credentialsId: 'huggingface-token', variable: 'HF_TOKEN')
                    ]) {
                        sh '''
                        pip install huggingface_hub
                        python -c "
from huggingface_hub import hf_hub_download
import shutil
import os

os.makedirs('machine_learning', exist_ok=True)

path1 = hf_hub_download(
    repo_id='ucdse/bike_availability_model',
    filename='bike_availability_model.pkl',
    token='${HF_TOKEN}'
)
shutil.copy(path1, 'machine_learning/bike_availability_model.pkl')

path2 = hf_hub_download(
    repo_id='ucdse/bike_availability_model',
    filename='model_features.pkl',
    token='${HF_TOKEN}'
)
shutil.copy(path2, 'machine_learning/model_features.pkl')

print('模型下载完成')
"
                        '''
                    }
                }
            }
        }

        stage('5. 构建并推送 Docker 镜像') {
            when {
                not { changeRequest() }
            }
            steps {
                container('docker') {
                    script {
                        def finalTag = params.IMAGE_TAG?.trim() ? params.IMAGE_TAG.trim() : env.BUILD_NUMBER
                        env.FULL_IMAGE = "${params.IMAGE_NAME}:${finalTag}"
                    }

                    withCredentials([
                        usernamePassword(
                            credentialsId: env.DOCKER_CREDENTIALS_ID,
                            usernameVariable: 'DOCKER_USER',
                            passwordVariable: 'DOCKER_PASS'
                        )
                    ]) {
                        sh '''
                        echo "${DOCKER_PASS}" | docker login -u "${DOCKER_USER}" --password-stdin
                        docker build -t ${FULL_IMAGE} .
                        if [ "${PUSH_IMAGE}" = "true" ] || [ "${DEPLOY_TO_EC2}" = "true" ]; then
                          docker push ${FULL_IMAGE}
                        fi
                        docker logout || true
                        '''
                    }
                }
            }
        }

        stage('6. 部署到 EC2') {
            when {
                allOf {
                    branch 'main'
                    not { changeRequest() }
                }
            }
            environment {
                CONTAINER_ENV_FILE = "${params.CONTAINER_ENV_FILE}"
            }
            steps {
                container('docker') {
                    withCredentials([
                        string(credentialsId: env.SERVER_HOST_CREDENTIALS_ID, variable: 'SERVER_HOST'),
                        sshUserPrivateKey(credentialsId: params.EC2_SSH_KEY_CREDENTIALS_ID, keyFileVariable: 'SSH_KEY', usernameVariable: 'SSH_USER'),
                        usernamePassword(credentialsId: env.DOCKER_CREDENTIALS_ID, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS'),
                        file(credentialsId: env.ENV_FILE_CREDENTIALS_ID, variable: 'ENV_FILE')
                    ]) {
                        sh '''
                        if command -v apk >/dev/null 2>&1; then
                          apk add --no-cache openssh-client bash
                        fi

                        # 在 EC2 上创建 .env 所在目录（若不存在）
                        ENV_DIR=$(dirname "${CONTAINER_ENV_FILE}")
                        ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${SSH_USER}@${SERVER_HOST}" "mkdir -p ${ENV_DIR}"

                        # 将 Jenkins 中的 .env credential 上传到 EC2 指定路径
                        scp -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${ENV_FILE}" "${SSH_USER}@${SERVER_HOST}:${CONTAINER_ENV_FILE}"

                        PASS_B64=$(printf '%s' "${DOCKER_PASS}" | base64)
                        USER_B64=$(printf '%s' "${DOCKER_USER}" | base64)
                        IMAGE_B64=$(printf '%s' "${FULL_IMAGE}" | base64)
                        NAME_B64=$(printf '%s' "${CONTAINER_NAME}" | base64)
                        ENV_FILE_B64=$(printf '%s' "${CONTAINER_ENV_FILE}" | base64)

                        ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${SSH_USER}@${SERVER_HOST}" \
                        "PASS_B64='${PASS_B64}' USER_B64='${USER_B64}' IMAGE_B64='${IMAGE_B64}' NAME_B64='${NAME_B64}' ENV_FILE_B64='${ENV_FILE_B64}' bash -s" <<'REMOTE'
set -e
DOCKER_PASS=$(echo "$PASS_B64" | base64 -d)
DOCKER_USER=$(echo "$USER_B64" | base64 -d)
FULL_IMAGE=$(echo "$IMAGE_B64" | base64 -d)
CONTAINER_NAME=$(echo "$NAME_B64" | base64 -d)
CONTAINER_ENV_FILE=$(echo "$ENV_FILE_B64" | base64 -d)

echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
docker pull "$FULL_IMAGE"
docker rm -f "$CONTAINER_NAME" || true
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  --network flask-app \
  --env-file "$CONTAINER_ENV_FILE" \
  "$FULL_IMAGE"
REMOTE
                        '''
                    }
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
