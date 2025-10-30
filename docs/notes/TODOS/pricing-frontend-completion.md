# Pricing Frontend Implementation - Remaining Work

## Status: Backend Complete ✅, Frontend Pending

### Completed
- ✅ Backend API models, repository, and routes
- ✅ Singleton pattern (one pricing per contract)
- ✅ GET and PUT endpoints working
- ✅ 3-field model: price_amount, price_currency, price_unit

### Remaining Work

## 1. Create PricingFormDialog Component

**Location:** `src/frontend/src/components/data-contracts/pricing-form-dialog.tsx` (new file)

```typescript
import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'

type Pricing = {
  price_amount?: string
  price_currency?: string
  price_unit?: string
}

type PricingFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (pricing: Pricing) => Promise<void>
  initial?: Pricing
}

export default function PricingFormDialog({ isOpen, onOpenChange, onSubmit, initial }: PricingFormProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [priceAmount, setPriceAmount] = useState('')
  const [priceCurrency, setPriceCurrency] = useState('')
  const [priceUnit, setPriceUnit] = useState('')

  useEffect(() => {
    if (isOpen) {
      setPriceAmount(initial?.price_amount || '')
      setPriceCurrency(initial?.price_currency || '')
      setPriceUnit(initial?.price_unit || '')
    }
  }, [isOpen, initial])

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      const pricing: Pricing = {
        price_amount: priceAmount.trim() || undefined,
        price_currency: priceCurrency.trim() || undefined,
        price_unit: priceUnit.trim() || undefined,
      }

      await onSubmit(pricing)
      onOpenChange(false)
      toast({
        title: 'Success',
        description: 'Pricing updated successfully'
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to update pricing',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Pricing</DialogTitle>
          <DialogDescription>
            Update pricing information for this data contract (ODCS compliant)
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Price Amount */}
            <div className="space-y-2">
              <Label htmlFor="price_amount">Price Amount</Label>
              <Input
                id="price_amount"
                value={priceAmount}
                onChange={(e) => setPriceAmount(e.target.value)}
                placeholder="e.g., 0.05, 100, Free"
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Numeric value or text (e.g., "Free")
              </p>
            </div>

            {/* Price Currency */}
            <div className="space-y-2">
              <Label htmlFor="price_currency">Currency</Label>
              <Input
                id="price_currency"
                value={priceCurrency}
                onChange={(e) => setPriceCurrency(e.target.value)}
                placeholder="e.g., USD, EUR, GBP"
                maxLength={10}
              />
              <p className="text-xs text-muted-foreground">
                Currency code (3-letter ISO)
              </p>
            </div>
          </div>

          {/* Price Unit */}
          <div className="space-y-2">
            <Label htmlFor="price_unit">Price Unit</Label>
            <Input
              id="price_unit"
              value={priceUnit}
              onChange={(e) => setPriceUnit(e.target.value)}
              placeholder="e.g., per GB, per query, per month"
              maxLength={50}
            />
            <p className="text-xs text-muted-foreground">
              Unit of measurement for pricing
            </p>
          </div>

          <div className="rounded-lg bg-muted p-3 text-sm">
            <p className="text-muted-foreground">
              <strong>Tip:</strong> Leave all fields empty to remove pricing information. All fields are optional.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

## 2. Add Pricing State Management to `data-contract-details.tsx`

**Location:** After line ~160 (after other dialog states)

```typescript
// Add to existing state declarations
const [isPricingFormOpen, setIsPricingFormOpen] = useState(false)
const [pricing, setPricing] = useState<{
  price_amount?: string
  price_currency?: string
  price_unit?: string
} | null>(null)
```

## 3. Import PricingFormDialog

**Location:** Top of file with other imports (around line 28)

```typescript
import PricingFormDialog from '@/components/data-contracts/pricing-form-dialog'
```

## 4. Add Pricing Fetch Function

**Location:** Add to fetch functions (around line 270)

```typescript
const fetchPricing = async () => {
  if (!contractId) return
  try {
    const response = await fetch(`/api/data-contracts/${contractId}/pricing`)
    if (response.ok) {
      const data = await response.json()
      setPricing(data)
    } else {
      setPricing(null)
    }
  } catch (e) {
    console.warn('Failed to fetch pricing:', e)
    setPricing(null)
  }
}
```

## 5. Call fetchPricing in useEffect

**Location:** In the main useEffect that calls fetchDetails (around line 260)

```typescript
useEffect(() => {
  if (contractId) {
    fetchDetails()
    fetchLinkedProducts()
    fetchContractTags()
    fetchSupportChannels()
    fetchPricing()  // Add this line
    fetchLatestProfilingRun()
  }
}, [contractId])
```

## 6. Add Pricing Update Handler

**Location:** Add after other handlers (around line 460)

```typescript
// Pricing handler (Edit only - singleton pattern)
const handleUpdatePricing = async (pricingData: any) => {
  if (!contractId) return

  try {
    const response = await fetch(`/api/data-contracts/${contractId}/pricing`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pricingData)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to update pricing')
    }

    await fetchPricing()
    toast({ title: 'Success', description: 'Pricing updated successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
    throw error
  }
}
```

## 7. Add Pricing UI Section

**Location:** Insert near SLA section (around line 1025, after SLA or before Team Members)

```tsx
{/* Pricing Section (ODCS Compliance) */}
<Card>
  <CardHeader>
    <div className="flex items-center justify-between">
      <div>
        <CardTitle className="text-xl">Pricing</CardTitle>
        <CardDescription>ODCS pricing information</CardDescription>
      </div>
      <Button
        size="sm"
        onClick={() => setIsPricingFormOpen(true)}
      >
        <Pencil className="h-4 w-4 mr-1.5" />
        Edit Pricing
      </Button>
    </div>
  </CardHeader>
  <CardContent>
    {pricing && (pricing.price_amount || pricing.price_currency || pricing.price_unit) ? (
      <div className="space-y-2">
        <div className="flex items-baseline gap-2">
          {pricing.price_amount && (
            <span className="text-2xl font-bold">{pricing.price_amount}</span>
          )}
          {pricing.price_currency && (
            <span className="text-lg text-muted-foreground">{pricing.price_currency}</span>
          )}
          {pricing.price_unit && (
            <span className="text-sm text-muted-foreground">/ {pricing.price_unit}</span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Click "Edit Pricing" to modify or clear pricing information
        </p>
      </div>
    ) : (
      <div className="text-center py-8">
        <p className="text-sm text-muted-foreground mb-3">
          No pricing information set
        </p>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setIsPricingFormOpen(true)}
        >
          <Pencil className="h-4 w-4 mr-1.5" />
          Set Pricing
        </Button>
      </div>
    )}
  </CardContent>
</Card>
```

## 8. Add PricingFormDialog Component

**Location:** Add at the end of the component, with other dialog components (around line 1380)

```tsx
{/* Pricing Form Dialog */}
<PricingFormDialog
  isOpen={isPricingFormOpen}
  onOpenChange={setIsPricingFormOpen}
  onSubmit={handleUpdatePricing}
  initial={pricing || undefined}
/>
```

## Alternative: Combined SLA & Pricing Section

**Location:** If you prefer to combine with SLA (around line 1025)

```tsx
{/* SLA & Pricing Section (ODCS Compliance) */}
<Card>
  <CardHeader>
    <CardTitle className="text-xl">SLA & Pricing</CardTitle>
    <CardDescription>Service level agreement and pricing information</CardDescription>
  </CardHeader>
  <CardContent className="space-y-6">
    {/* SLA Properties */}
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">Service Level Agreement</h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setIsSlaFormOpen(true)}
        >
          <Pencil className="h-4 w-4 mr-1.5" />
          Edit SLA
        </Button>
      </div>
      {/* Existing SLA display */}
    </div>

    <Separator />

    {/* Pricing */}
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">Pricing</h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setIsPricingFormOpen(true)}
        >
          <Pencil className="h-4 w-4 mr-1.5" />
          Edit Pricing
        </Button>
      </div>
      {pricing && (pricing.price_amount || pricing.price_currency || pricing.price_unit) ? (
        <div className="flex items-baseline gap-2">
          {pricing.price_amount && (
            <span className="text-2xl font-bold">{pricing.price_amount}</span>
          )}
          {pricing.price_currency && (
            <span className="text-lg text-muted-foreground">{pricing.price_currency}</span>
          )}
          {pricing.price_unit && (
            <span className="text-sm text-muted-foreground">/ {pricing.price_unit}</span>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No pricing set</p>
      )}
    </div>
  </CardContent>
</Card>
```

## Testing Checklist

- [ ] Edit pricing with all fields filled
- [ ] Edit pricing with only some fields filled
- [ ] Clear all pricing fields (set to empty)
- [ ] Verify pricing persists after page reload
- [ ] Check empty state displays correctly
- [ ] Verify "Edit Pricing" button works
- [ ] Test with various price formats (numeric, text like "Free")
- [ ] Verify currency codes display correctly
- [ ] Check responsive layout

## Integration Points

- Pricing is fetched via `/api/data-contracts/{id}/pricing`
- Pricing is updated via PUT (no POST/DELETE - singleton pattern)
- Returns empty structure if pricing doesn't exist
- Automatically creates pricing record on first update
- All fields are optional

## File References

- Backend: `src/backend/src/routes/data_contracts_routes.py` (lines 3373-3463)
- API Models: `src/backend/src/models/data_contracts_api.py` (lines 546-563)
- Repository: `src/backend/src/repositories/data_contracts_repository.py` (lines 389-451)
- Form Dialog: `src/frontend/src/components/data-contracts/pricing-form-dialog.tsx` (to be created)
- Main View: `src/frontend/src/views/data-contract-details.tsx` (needs integration)

## Additional Notes

- **Singleton Pattern**: Only one pricing record per contract (like SLA)
- **Edit Only**: No Add/Delete operations, only GET and PUT
- **All Optional**: All 3 fields are optional
- **ODCS Field**: Maps to `price` object in ODCS v3.0.2 specification
- **Display Format**: Shows amount, currency, and unit in a clean format
- **Empty State**: Provides both message and button to set pricing
- **Auto-Create**: First PUT automatically creates the pricing record
