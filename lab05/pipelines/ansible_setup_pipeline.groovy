// Конвейер настройки тестового сервера плейбуком setup_test_server.yml на агенте Ansible.
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
                // Клонирование репозитория с плейбуком.
                checkout scm
            }
        }

        stage('Run Playbook') {
            steps {
                // Закрытый ключ пользователя ansible берётся из учётных данных Jenkins
                // и существует только на время выполнения блока withCredentials.
                dir('lab05/ansible') {
                    sh 'ansible --version'
                    withCredentials([sshUserPrivateKey(credentialsId: 'ansible-test-server-key', keyFileVariable: 'ANSIBLE_KEY')]) {
                        sh 'ansible-playbook setup_test_server.yml --syntax-check'
                        sh 'ansible-playbook setup_test_server.yml --private-key "$ANSIBLE_KEY"'
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'Test server configured successfully.'
        }
        failure {
            echo 'Test server configuration failed.'
        }
    }
}
