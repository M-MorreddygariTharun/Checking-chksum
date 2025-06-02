pipeline {
    agent any

    environment {
        URL_TO_SCAN = 'http://172.18.6.250/Deepscreen_cron/QNX/High_IPC_QNX/06_02_2025/'
    }

    stages {
        stage('Install Dependencies') {
            steps {
                bat 'pip install -r requirements.txt'
            }
        }

        stage('Run Checksum Script') {
            steps {
                bat 'python chksum.py %URL_TO_SCAN%'
            }
        }
    }

    post {
        always {
            echo 'Pipeline completed.'
        }
    }
}
