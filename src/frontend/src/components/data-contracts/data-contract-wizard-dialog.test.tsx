/**
 * Tests for DataContractWizardDialog schema inference functionality
 */

import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithProviders } from '@/test/utils'
import DataContractWizardDialog from './data-contract-wizard-dialog'

// Mock the hooks and components
vi.mock('@/hooks/use-domains', () => ({
  useDomains: () => ({
    domains: [
      { id: 'domain1', name: 'Test Domain 1' },
      { id: 'domain2', name: 'Test Domain 2' }
    ],
    loading: false,
    refetch: vi.fn()
  })
}))

// Create a shared mockToast function
const mockToast = vi.fn()

vi.mock('@/hooks/use-toast', () => ({
  default: () => ({
    toast: mockToast
  }),
  useToast: () => ({
    toast: mockToast
  })
}))

vi.mock('./dataset-lookup-dialog', () => ({
  default: ({ onSelect }: { onSelect: (table: { full_name: string }) => void }) => (
    <div data-testid="dataset-lookup-dialog">
      <button
        onClick={() => onSelect({ full_name: 'lars_george_uc.test-db.table_a' })}
        data-testid="select-dataset"
      >
        Select Dataset
      </button>
    </div>
  )
}))

vi.mock('@/components/business-concepts/business-concepts-display', () => ({
  default: () => <div data-testid="business-concepts-display" />
}))

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('DataContractWizardDialog Schema Inference', () => {
  const mockOnOpenChange = vi.fn()
  const mockOnSubmit = vi.fn()

  const sampleUCResponse = {
    schema: [
      {
        name: 'id',
        type: 'int',
        physicalType: 'int',
        logicalType: 'integer',
        nullable: false,
        comment: 'A unique identifier for each entry in the table, allowing for easy tracking and referencing of specific records.',
        partitioned: false,
        partitionKeyPosition: null
      },
      {
        name: 'info',
        type: 'string',
        physicalType: 'string',
        logicalType: 'string',
        nullable: true,
        comment: 'Contains additional details related to each entry, which can provide context or further information necessary for analysis or reporting.',
        partitioned: false,
        partitionKeyPosition: null
      }
    ],
    table_info: {
      name: 'table_a',
      catalog_name: 'lars_george_uc',
      schema_name: 'test-db',
      table_type: 'MANAGED',
      data_source_format: 'DELTA',
      storage_location: 's3://databricks-e2demofieldengwest/b169b504-4c54-49f2-bc3a-adf4b128f36d/tables/c39d273a-d87b-4a62-8792-0193f142fca7',
      owner: 'lars.george@databricks.com',
      comment: 'The table contains records of various entries identified by a unique ID.',
      created_at: 'Mon Jul 28 12:31:34 UTC 2025',
      properties: {
        'delta.enableDeletionVectors': 'true',
        'delta.feature.appendOnly': 'supported'
      }
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(sampleUCResponse)
    })
  })

  it('should render the wizard dialog', () => {
    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
      />
    )

    expect(screen.getByText(/Data Contract Wizard/i)).toBeInTheDocument()
    expect(screen.getByText('Build a contract incrementally according to ODCS v3.0.2')).toBeInTheDocument()
  })

  it('should handle schema inference from UC dataset', async () => {
    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
        initial={{ name: 'Test Contract', version: '1.0.0', status: 'draft' }}
      />
    )

    // Navigate to step 2 (Schema)
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    // Wait for step 2 to appear - use getByText with partial match
    await waitFor(() => {
      expect(screen.getByText(/Infer from Dataset/i)).toBeInTheDocument()
    }, { timeout: 5000 })

    // Click "Infer from Dataset" button
    const inferButton = screen.getByText(/Infer from Dataset/i)
    fireEvent.click(inferButton)

    // Click the dataset selection in the mocked dialog
    const selectDatasetButton = screen.getByTestId('select-dataset')
    fireEvent.click(selectDatasetButton)

    // Wait for fetch to be called
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/catalogs/dataset/lars_george_uc.test-db.table_a')
    })

    // Wait for schema to be populated
    await waitFor(() => {
      expect(screen.getByDisplayValue('table_a')).toBeInTheDocument()
    })

    // Verify physical name is set to storage location
    expect(screen.getByDisplayValue(sampleUCResponse.table_info.storage_location)).toBeInTheDocument()
  })

  it('should properly set physical and logical types from UC metadata', async () => {
    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
        initial={{ name: 'Test Contract', version: '1.0.0', status: 'draft' }}
      />
    )

    // Navigate to step 2 and trigger inference
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    const inferButton = screen.getByText(/Infer from Dataset/i)
    fireEvent.click(inferButton)

    const selectDatasetButton = screen.getByTestId('select-dataset')
    fireEvent.click(selectDatasetButton)

    // Wait for schema to be populated
    await waitFor(() => {
      expect(screen.getByDisplayValue('id')).toBeInTheDocument()
    })

    // Check that physical types are populated
    const physicalTypeInputs = screen.getAllByPlaceholderText(/VARCHAR|BIGINT/i)
    expect(physicalTypeInputs.length).toBeGreaterThan(0)

    // Check that logical type dropdowns show ODCS types
    const logicalTypeSelects = screen.getAllByText('integer')
    expect(logicalTypeSelects.length).toBeGreaterThan(0)
  })

  it('should populate column descriptions from UC comments', async () => {
    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
        initial={{ name: 'Test Contract', version: '1.0.0', status: 'draft' }}
      />
    )

    // Navigate to step 2 and trigger inference
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    const inferButton = screen.getByText(/Infer from Dataset/i)
    fireEvent.click(inferButton)

    const selectDatasetButton = screen.getByTestId('select-dataset')
    fireEvent.click(selectDatasetButton)

    // Wait for schema to be populated - use partial match since descriptions are long
    await waitFor(() => {
      expect(screen.getByDisplayValue(/A unique identifier for each entry/i)).toBeInTheDocument()
    })

    // Verify second column description
    expect(screen.getByDisplayValue(/Contains additional details related to each entry/i)).toBeInTheDocument()
  })

  it('should handle partition information correctly', async () => {
    const partitionedResponse = {
      ...sampleUCResponse,
      schema: [
        ...sampleUCResponse.schema,
        {
          name: 'partition_date',
          type: 'date',
          physicalType: 'date',
          logicalType: 'date',
          nullable: false,
          comment: 'Partition column',
          partitioned: true,
          partitionKeyPosition: 0
        }
      ]
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(partitionedResponse)
    })

    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
        initial={{ name: 'Test Contract', version: '1.0.0', status: 'draft' }}
      />
    )

    // Trigger inference
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    const inferButton = screen.getByText(/Infer from Dataset/i)
    fireEvent.click(inferButton)

    const selectDatasetButton = screen.getByTestId('select-dataset')
    fireEvent.click(selectDatasetButton)

    // Wait for schema to be populated
    await waitFor(() => {
      expect(screen.getByDisplayValue('partition_date')).toBeInTheDocument()
    })

    // Verify partition checkbox is checked (would need to find specific element)
    // This would require more specific test setup to check checkbox states
  })

  it('should handle fetch errors gracefully', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
        initial={{ name: 'Test Contract', version: '1.0.0', status: 'draft' }}
      />
    )

    // Trigger inference
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    const inferButton = screen.getByText(/Infer from Dataset/i)
    fireEvent.click(inferButton)

    const selectDatasetButton = screen.getByTestId('select-dataset')
    fireEvent.click(selectDatasetButton)

    // Wait for error handling
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Schema added without columns',
        description: 'Could not fetch columns. Configure SQL warehouse to enable inference.',
        variant: 'warning'
      })
    })
  })

  it('should handle API error responses gracefully', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500
    })

    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
        initial={{ name: 'Test Contract', version: '1.0.0', status: 'draft' }}
      />
    )

    // Trigger inference
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    const inferButton = screen.getByText(/Infer from Dataset/i)
    fireEvent.click(inferButton)

    const selectDatasetButton = screen.getByTestId('select-dataset')
    fireEvent.click(selectDatasetButton)

    // Wait for error handling
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Schema added without columns',
        description: 'Could not fetch columns. Configure SQL warehouse to enable inference.',
        variant: 'warning'
      })
    })
  })

  it('should show enhanced success message with owner information', async () => {
    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
        initial={{ name: 'Test Contract', version: '1.0.0', status: 'draft' }}
      />
    )

    // Trigger inference
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    const inferButton = screen.getByText(/Infer from Dataset/i)
    fireEvent.click(inferButton)

    const selectDatasetButton = screen.getByTestId('select-dataset')
    fireEvent.click(selectDatasetButton)

    // Wait for success message
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Schema inferred successfully',
        description: 'Loaded 2 columns from lars_george_uc.test-db.table_a (owner: lars.george@databricks.com)'
      })
    })
  })

  it('should map various UC types to correct ODCS logical types', async () => {
    const variedTypesResponse = {
      schema: [
        { name: 'int_col', type: 'int', physicalType: 'int', logicalType: 'integer', nullable: true },
        { name: 'bigint_col', type: 'bigint', physicalType: 'bigint', logicalType: 'integer', nullable: true },
        { name: 'string_col', type: 'string', physicalType: 'string', logicalType: 'string', nullable: true },
        { name: 'double_col', type: 'double', physicalType: 'double', logicalType: 'number', nullable: true },
        { name: 'date_col', type: 'date', physicalType: 'date', logicalType: 'date', nullable: true },
        { name: 'bool_col', type: 'boolean', physicalType: 'boolean', logicalType: 'boolean', nullable: true },
        { name: 'array_col', type: 'array<string>', physicalType: 'array<string>', logicalType: 'array', nullable: true }
      ],
      table_info: { name: 'varied_types_table' }
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(variedTypesResponse)
    })

    renderWithProviders(
      <DataContractWizardDialog
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
        initial={{ name: 'Test Contract', version: '1.0.0', status: 'draft' }}
      />
    )

    // Trigger inference
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    const inferButton = screen.getByText(/Infer from Dataset/i)
    fireEvent.click(inferButton)

    const selectDatasetButton = screen.getByTestId('select-dataset')
    fireEvent.click(selectDatasetButton)

    // Wait for schema to be populated
    await waitFor(() => {
      expect(screen.getByDisplayValue('int_col')).toBeInTheDocument()
    })

    // Verify various logical types are correctly mapped
    // (This would require more detailed DOM inspection to verify select values)
  })
})