DROP TABLE IF EXISTS files;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS records;


CREATE TABLE IF NOT EXISTS users (
    user_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id)
);


CREATE TABLE IF NOT EXISTS files (
    file_id INT NOT NULL AUTO_INCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash VARCHAR(255) NOT NULL,
    algorithm VARCHAR(12) NOT NULL,
    bucket VARCHAR(255) NOT NULL,
    size SMALLINT NOT NULL,
    arn VARCHAR(255) NOT NULL,

    PRIMARY KEY (file_id)
);


CREATE TABLE IF NOT EXISTS records (
    record_id INT NOT NULL AUTO_INCREMENT,
    file_id INT,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    folder VARCHAR(128),

    PRIMARY KEY (record_id),
    FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);


INSERT INTO users (user_id, name) VALUES (10001, "Alex"), (10002, "John"), (10003, "Bob");

