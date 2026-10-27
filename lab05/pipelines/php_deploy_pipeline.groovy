// Конвейер развёртывания isbn-tools на тестовом сервере плейбуком deploy_isbn_tools.yml.
pipeline {
    agent {
        label 'ansible-agent'
    }

    options {
        skipDefaultCheckout()
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                // Клонирование репозитория с PHP-проектом и плейбуком развёртывания.
                checkout scm
            }
        }

        stage('Copy Files') {
            steps {
                // Копирование файлов проекта на сервер (тег copy).
                dir('lab05/ansible') {
                    withCredentials([sshUserPrivateKey(credentialsId: 'ansible-test-server-key', keyFileVariable: 'ANSIBLE_KEY')]) {
                        sh 'ansible-playbook deploy_isbn_tools.yml --syntax-check'
                        sh 'ansible-playbook deploy_isbn_tools.yml --tags copy --private-key "$ANSIBLE_KEY"'
                    }
                }
            }
        }

        stage('Configure') {
            steps {
                // Composer без dev-пакетов, владелец и права файлов, контрольный запрос к странице (тег configure).
                dir('lab05/ansible') {
                    withCredentials([sshUserPrivateKey(credentialsId: 'ansible-test-server-key', keyFileVariable: 'ANSIBLE_KEY')]) {
                        sh 'ansible-playbook deploy_isbn_tools.yml --tags configure --private-key "$ANSIBLE_KEY"'
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'isbn-tools deployed successfully.'
        }
        failure {
            echo 'isbn-tools deployment failed.'
        }
    }
}
