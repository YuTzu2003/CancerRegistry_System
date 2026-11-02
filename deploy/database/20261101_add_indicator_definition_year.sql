/*
  A definition snapshot is selected independently from the diagnosis-year
  range.  definition_year is therefore only its intended annual edition; it
  never filters the uploaded cases automatically.
*/
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF COL_LENGTH(N'dbo.IndicatorDefinitionVersion', N'definition_year') IS NULL
BEGIN
    ALTER TABLE dbo.IndicatorDefinitionVersion
        ADD definition_year int NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.IndicatorDefinitionVersion')
      AND name = N'CK_IndicatorDefinitionVersion_DefinitionYear'
)
BEGIN
    ALTER TABLE dbo.IndicatorDefinitionVersion WITH CHECK
        ADD CONSTRAINT CK_IndicatorDefinitionVersion_DefinitionYear
        CHECK (definition_year IS NULL OR definition_year BETWEEN 1 AND 9999);
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.IndicatorDefinitionVersion')
      AND name = N'IX_IndicatorDefinitionVersion_DefinitionYear'
)
BEGIN
    CREATE INDEX IX_IndicatorDefinitionVersion_DefinitionYear
        ON dbo.IndicatorDefinitionVersion (definition_year DESC, version_id DESC);
END;

COMMIT TRANSACTION;
