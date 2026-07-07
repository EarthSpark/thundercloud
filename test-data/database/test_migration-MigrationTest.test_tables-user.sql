CREATE TABLE "user" (
    username VARCHAR(100),
    password VARCHAR(255),
    email VARCHAR(255),
    fs_uniquifier VARCHAR(255) NOT NULL,
    portal_id CHAR(32),
    active BOOLEAN,
    locale VARCHAR,
    api_sales_account_id CHAR(32),
    account_all_access BOOLEAN NOT NULL,
    ground_all_access BOOLEAN NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (fs_uniquifier),
    UNIQUE (portal_id),
    FOREIGN KEY(api_sales_account_id) REFERENCES sales_account (id)
)

