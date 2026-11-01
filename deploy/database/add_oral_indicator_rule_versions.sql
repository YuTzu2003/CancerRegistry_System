IF OBJECT_ID(N'dbo.OralIndicatorRuleVersion', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.OralIndicatorRuleVersion (
        version_id int IDENTITY(1,1) NOT NULL PRIMARY KEY,
        version_name nvarchar(100) NOT NULL,
        rules_json nvarchar(max) NOT NULL,
        created_by nvarchar(100) NOT NULL,
        created_at datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_OralIndicatorRuleVersion_Name UNIQUE (version_name),
        CONSTRAINT CK_OralIndicatorRuleVersion_Json CHECK (ISJSON(rules_json) = 1)
    );
END
