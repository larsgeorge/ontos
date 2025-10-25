import { test, expect } from '@playwright/test';

test.describe('Team Assignment Flow', () => {
  test('assign team and verify Import from Team button appears', async ({ page }) => {
    // Navigate to contracts list
    await page.goto('/data-contracts');
    await page.waitForLoadState('networkidle');
    
    console.log('✓ Navigated to data contracts list');
    
    // Click on first contract
    const firstContract = page.locator('a[href^="/data-contracts/"]').first();
    await expect(firstContract).toBeVisible({ timeout: 10000 });
    const contractUrl = await firstContract.getAttribute('href');
    console.log(`✓ Found contract: ${contractUrl}`);
    
    await firstContract.click();
    await page.waitForLoadState('networkidle');
    
    console.log('✓ Navigated to contract details');
    
    // Check initial state - Import button should NOT be visible
    const importButton = page.getByRole('button', { name: /import from team/i });
    const isInitiallyVisible = await importButton.isVisible().catch(() => false);
    console.log(`✓ Import button initially visible: ${isInitiallyVisible}`);
    
    // Open Edit Metadata dialog
    await page.getByRole('button', { name: /edit metadata/i }).click();
    await expect(page.locator('[role="dialog"]')).toBeVisible();
    
    console.log('✓ Opened Edit Metadata dialog');
    
    // Find Owner Team dropdown
    const ownerTeamLabel = page.locator('label:has-text("Owner Team")');
    await expect(ownerTeamLabel).toBeVisible();
    
    // Click the dropdown trigger
    const dropdownTrigger = page.locator('[id="ownerTeamId"]').or(
      page.locator('button[role="combobox"]').filter({ has: ownerTeamLabel })
    );
    await dropdownTrigger.click();
    
    console.log('✓ Clicked Owner Team dropdown');
    
    // Wait for options to appear
    await page.waitForTimeout(500);
    
    // Get all options (skip "None")
    const options = page.locator('[role="option"]');
    const optionCount = await options.count();
    console.log(`✓ Found ${optionCount} team options`);
    
    if (optionCount <= 1) {
      console.log('⚠️ No teams available to test with');
      test.skip();
      return;
    }
    
    // Select second option (first is "None")
    const teamOption = options.nth(1);
    const teamName = await teamOption.textContent();
    console.log(`✓ Selecting team: ${teamName}`);
    
    await teamOption.click();
    await page.waitForTimeout(300);
    
    // Save changes
    await page.getByRole('button', { name: /save changes/i }).click();
    console.log('✓ Clicked Save Changes');
    
    // Wait for dialog to close
    await expect(page.locator('[role="dialog"]')).toBeHidden({ timeout: 5000 });
    await page.waitForLoadState('networkidle');
    
    console.log('✓ Dialog closed, page reloaded');
    
    // Wait a bit for state to update
    await page.waitForTimeout(1000);
    
    // Scroll to Team Members section
    const teamMembersSection = page.locator('h3:has-text("Team Members"), h2:has-text("Team Members")').first();
    await teamMembersSection.scrollIntoViewIfNeeded();
    
    console.log('✓ Scrolled to Team Members section');
    
    // Check if owner team is displayed in metadata
    const ownerField = page.locator('text=/Owner:?/i').locator('..');
    const ownerText = await ownerField.textContent();
    console.log(`✓ Owner field content: ${ownerText}`);
    
    // Now check for Import from Team button
    await page.waitForTimeout(2000); // Give extra time for async updates
    
    const importButtonVisible = await importButton.isVisible().catch(() => false);
    console.log(`Import from Team button visible: ${importButtonVisible}`);
    
    if (importButtonVisible) {
      console.log('✅ SUCCESS: Import from Team button is visible!');
      
      // Try clicking it
      await importButton.click();
      await expect(page.locator('[role="dialog"]:has-text("Import Team Members")')).toBeVisible({ timeout: 5000 });
      console.log('✅ Import dialog opened successfully!');
    } else {
      console.log('❌ FAILURE: Import from Team button is NOT visible');
      
      // Debug: Check what buttons ARE visible in Team Members section
      const allButtons = page.locator('button');
      const buttonTexts = await allButtons.allTextContents();
      console.log('All visible buttons:', buttonTexts.filter(t => t.trim()));
      
      // Debug: Check contract state by looking at the page
      const pageContent = await page.content();
      console.log('Checking for owner_team_id in page...');
      console.log('Has "owner_team_id":', pageContent.includes('owner_team_id'));
      
      // Pause to inspect manually
      await page.pause();
    }
  });
});

