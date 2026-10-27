// Конвейер сборки и тестирования проекта isbn-tools на SSH-агенте.
pipeline {
    // Сборка выполняется только на SSH-агенте с меткой php-agent.
    agent {
        label 'php-agent'
    }

    // Получение репозитория выполняется явной стадией Checkout.
    options {
        skipDefaultCheckout()
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
    }

    // Каталог PHP-проекта относительно корня репозитория.
    environment {
        PROJECT_DIR = 'lab05/isbn-tools'
    }

    stages {
        stage('Checkout') {
            steps {
                // Клонирование репозитория с PHP-проектом.
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                // Проверка окружения, проверка composer.json и установка зависимостей из composer.lock.
                echo 'Preparing project...'
                dir("${PROJECT_DIR}") {
                    sh 'php --version'
                    sh 'composer --version'
                    sh 'composer validate --strict'
                    sh 'composer install --no-interaction --no-progress --prefer-dist'
                }
            }
        }

        stage('Test') {
            steps {
                // Запуск модульных тестов PHPUnit с отчётом в формате JUnit.
                echo 'Running tests...'
                dir("${PROJECT_DIR}") {
                    sh 'vendor/bin/phpunit --log-junit build/junit.xml'
                }
            }
        }

        stage('Report') {
            steps {
                // Публикация результатов тестов в Jenkins.
                junit testResults: "${PROJECT_DIR}/build/junit.xml"
            }
        }
    }

    post {
        always {
            echo 'Pipeline completed.'
        }
        success {
            echo 'All stages completed successfully!'
        }
        failure {
            echo 'Errors detected in the pipeline.'
        }
    }
}
