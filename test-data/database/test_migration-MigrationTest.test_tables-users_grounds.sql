CREATE TABLE users_grounds (
    ground_id CHAR(32) NOT NULL,
    user_id CHAR(32) NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(ground_id) REFERENCES ground (id),
    FOREIGN KEY(user_id) REFERENCES "user" (id)
)

