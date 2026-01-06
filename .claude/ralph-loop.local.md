---
active: true
iteration: 9
max_iterations: 0
completion_promise: null
started_at: "2026-01-06T09:00:32Z"
---

BowlerProfile Design System Integration Plan
Overview
Transform BowlerProfile.jsx to match the design system patterns established in PlayerProfile.jsx. This will create a mobile-optimized, web-optimized, shareable, and responsive experience with consistent styling and improved UX.
Key Changes Summary
Filter Architecture: Desktop sidebar (280px, sticky) + Mobile bottom drawer with filter count badge
Layout: Two-column responsive layout (sidebar + main content)
Component Wrapping: All visualizations wrapped in VisualizationCard, stats in Section
Design Tokens: Replace all inline styles with tokens from designSystem.js
Loading States: Comprehensive skeleton loading via BowlerProfileLoadingState
Mobile UX: MobileStickyHeader with collapse functionality
Accessibility: ARIA labels on all visualizations
Implementation Phases
Phase 1: Create New Files
1.1 Create src/components/bowlerProfile/filterConfig.js
Export filter configuration following the pattern in playerProfile/filterConfig.js:
DEFAULT_START_DATE = '2020-01-01'
TODAY = new Date().toISOString().split('T')[0]
buildBowlerProfileFilters({ players, venues }) returning array of filter objects
Filter objects structure:

{ key, label, type, options?, defaultValue, required?, group? }
Filters needed:
Player (autocomplete, required)
Start Date (date, group: 'dateRange')
End Date (date, group: 'dateRange')
Venue (autocomplete)
1.2 Create src/components/bowlerProfile/BowlerProfileLoadingState.jsx
Skeleton loading states matching the three bowling sections: Overview Section (columns: '1fr'):
Skeleton.Grid for career stats cards (6 items)
Card skeleton for PlayerDNASummary
(ContextualQueryPrompts doesn't need skeleton)
Bowling Performance Section (columns: 2-column grid on desktop):
4 VisualizationCard skeletons with chart placeholders (220px mobile, 280px desktop height)
Titles: "Wicket Distribution", "Over Economy", "Frequent Overs", "Over Combinations"
Innings Details Section (columns: '1fr'):
1 VisualizationCard skeleton for BowlingInningsTable
Use design system tokens throughout: spacing, borderRadius, colors
Phase 2: Transform BowlerProfile.jsx
2.1 Update Imports (Lines 1-14)
Remove: Direct MUI imports (TextField, CircularProgress, Alert, Autocomplete), CompetitionFilter import Add:

import { Chip, useMediaQuery, useTheme } from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';

// Design System
import { AlertBanner, MobileStickyHeader, Section, VisualizationCard } from './ui';
import { colors, spacing, typography, borderRadius, zIndex } from '../theme/designSystem';

// Filter Architecture
import FilterBar from './bowlerProfile/FilterBar';
import FilterSheet from './bowlerProfile/FilterSheet';
import { buildBowlerProfileFilters, DEFAULT_START_DATE, TODAY } from './bowlerProfile/filterConfig';
import BowlerProfileLoadingState from './bowlerProfile/BowlerProfileLoadingState';
Keep: Container, Box, Button from MUI; all bowling component imports
2.2 Component Setup (Lines 16-44)
Remove:
DEFAULT_START_DATE and TODAY constants (now from filterConfig)
isMobile prop from function signature
Add after line 21 (after useNavigate):

const theme = useTheme();
const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
Add after line 44 (after dnaFetchTrigger state):

const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
2.3 Add Filter Handlers & Memoized Values (After line 192)
Add these functions following PlayerProfile pattern:
handleFilterChange(key, value) - Updates individual filter values
handleApplyFilters(nextValues, nextCompetitionFilters) - Applies all filters from mobile sheet
activeFilterCount (useMemo) - Counts active non-default filters
filterConfig (useMemo) - Builds filter config from buildBowlerProfileFilters
filterValues (useMemo) - Current filter values object
Active filter count logic:
Venue !== 'All Venues' (+1)
Start date !== DEFAULT_START_DATE (+1)
End date !== TODAY (+1)
Competition international === true (+1)
Competition topTeams !== 10 (+1 if international)
2.4 Add Mobile Filter Button (After useMemo blocks)
Create mobileFilterButton component:
Outlined button with FilterListIcon
Shows "Filters" text
Displays filter count Chip badge when activeFilterCount > 0
Uses design system tokens for all styling
onClick: setFilterDrawerOpen(true)
Min height: 44px (touch target)
2.5 Transform JSX Layout (Lines 244-360)
Container & Error (Lines 244-247):
Update py to isMobile ? 2 : 4
Replace <Alert> with <AlertBanner>
Add Mobile Headers (After error, before filters): When isMobile && stats:

<MobileStickyHeader
  title={selectedPlayer || 'Bowler Profile'}
  action={mobileFilterButton}
  enableCollapse
/>
When isMobile && !stats:

<Box sx={{ sticky header box with title and filter button }} />
Two-Column Layout (Replace lines 249-306): Create flex layout with:
Desktop: Sidebar (280px) + Main content (flex: 1)
Mobile: Stack vertically
Desktop Sidebar (shown when !isMobile):
Width: 280px, sticky, top: 32px
Bordered card wrapper with "Filters" heading
Contains <FilterBar> component with all props
Main Content Area:
flex: 1, minWidth: 0
Contains loading state and stats
Loading State (Replace lines 308-312):

{loading && <BowlerProfileLoadingState isMobile={isMobile} />}
Stats Content (Replace lines 314-357): Reorganize into three sections:
Overview Section (disableTopSpacing, columns: '1fr'):
<BowlingCareerStatsCards stats={stats} isMobile={isMobile} />
<PlayerDNASummary> (with playerType="bowler", isMobile prop)
<ContextualQueryPrompts> (with isMobile prop)
Bowling Performance Section (columns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }):
Title: "Bowling Performance"
Subtitle: "Phase-wise wickets, economy rates, and over-by-over analysis"
4 charts wrapped in VisualizationCard:
WicketDistribution (ariaLabel: "Wicket distribution by phase")
OverEconomyChart (ariaLabel: "Over-by-over economy analysis")
FrequentOversChart (ariaLabel: "Frequent overs bowled")
OverCombinationsChart (ariaLabel: "Over combination patterns")
Each chart: <ChartComponent stats={stats} isMobile={isMobile} wrapInCard={false} />
Innings Details Section (columns: '1fr'):
Title: "Innings Details"
Subtitle: "Complete breakdown of individual bowling performances"
<BowlingInningsTable stats={stats} isMobile={isMobile} wrapInCard={false} />
FilterSheet (After closing main content Box):

<FilterSheet
  open={filterDrawerOpen}
  onClose={() => setFilterDrawerOpen(false)}
  filters={filterConfig}
  values={filterValues}
  competitionFilters={competitionFilters}
  onApply={handleApplyFilters}
  loading={loading}
/>
Phase 3: Update Child Components
Apply this pattern to all bowling visualization components:
Pattern for Each Chart Component
Components to update:
BowlingCareerStatsCards.jsx
WicketDistribution.jsx
OverEconomyChart.jsx
FrequentOversChart.jsx
OverCombinationsChart.jsx
BowlingInningsTable.jsx
Changes for each:
Add imports: spacing, colors, typography, borderRadius, shadows from designSystem
Update signature: Add isMobile = false, wrapInCard = true props
Remove: Internal isMobile detection (useTheme, useMediaQuery)
Update styles: Replace all hardcoded values with design tokens
Spacing: Use spacing.xs, spacing.sm, spacing.base, spacing.lg
Colors: Use colors.neutral[X], colors.primary[X]
Border radius: Use borderRadius.base
Shadows: Use shadows.sm, shadows.base
Typography: Use typography.fontWeight.semibold, typography.fontSize.xs
Conditional wrapping:

const content = <>{/* chart content */}</>;

if (!wrapInCard) return content;

return (
  <Card sx={{ design system styles }}>
    <CardContent sx={{ p: isMobile ? spacing.base : spacing.lg }}>
      {content}
    </CardContent>
  </Card>
);
Special Case: BowlingCareerStatsCards
This component should:
Accept isMobile prop
Use design tokens for Grid spacing, Card styles
Apply responsive padding based on isMobile
Not need wrapInCard (it renders multiple cards)
Phase 4: Copy Filter Components
Since FilterBar and FilterSheet are nearly identical to playerProfile versions: Option A (Recommended): Reuse playerProfile components directly
Import FilterBar/FilterSheet from ../playerProfile/
Only create bowlerProfile/filterConfig.js and bowlerProfile/BowlerProfileLoadingState.jsx
Option B: Copy and adapt
Copy playerProfile/FilterBar.jsx → bowlerProfile/FilterBar.jsx
Copy playerProfile/FilterSheet.jsx → bowlerProfile/FilterSheet.jsx
Update imports to reference bowlerProfile/filterConfig
Choose Option A to reduce code duplication.
Testing Checklist
Desktop Experience
 Sidebar is sticky at 280px width
 All filters work (player, dates, venue, competition)
 GO button triggers fetch
 Stats display in 3 clear sections
 All visualizations wrapped in VisualizationCard
 Hover states work on cards
 Design tokens consistently applied
Mobile Experience
 MobileStickyHeader shows when stats loaded
 Filter button shows with badge count
 FilterSheet opens from bottom
 Touch targets are 44px minimum
 Sections stack vertically
 Charts are responsive
Loading & Errors
 BowlerProfileLoadingState shows proper skeletons
 Errors display via AlertBanner
 Loading transition is smooth
URL & Sharing
 URL updates with filter changes
 Shared URLs load correct player/filters
 autoload=true triggers automatic fetch
Accessibility
 All VisualizationCards have aria-label
 Keyboard navigation works
 Focus states visible
Critical Files Modified
src/components/BowlerProfile.jsx - 400+ lines changed (main transformation)
src/components/BowlingCareerStatsCards.jsx - Add isMobile, design tokens
src/components/WicketDistribution.jsx - Add isMobile/wrapInCard, tokens
src/components/OverEconomyChart.jsx - Add isMobile/wrapInCard, tokens
src/components/FrequentOversChart.jsx - Add isMobile/wrapInCard, tokens
src/components/OverCombinationsChart.jsx - Add isMobile/wrapInCard, tokens
src/components/BowlingInningsTable.jsx - Add isMobile/wrapInCard, tokens
New Files Created
src/components/bowlerProfile/filterConfig.js - Filter configuration
src/components/bowlerProfile/BowlerProfileLoadingState.jsx - Loading skeletons
Dependencies
All required UI components already exist:
src/components/ui/AlertBanner.jsx
src/components/ui/MobileStickyHeader.jsx
src/components/ui/Section.jsx
src/components/ui/VisualizationCard.jsx
src/components/ui/Card.jsx
src/components/ui/Skeleton.jsx
src/components/playerProfile/FilterBar.jsx (reusable)
src/components/playerProfile/FilterSheet.jsx (reusable)
Section Structure Summary
Overview (1 column):
BowlingCareerStatsCards (6 stat cards)
PlayerDNASummary (bowling DNA)
ContextualQueryPrompts (query links)
Bowling Performance (2 columns on desktop):
WicketDistribution
OverEconomyChart
FrequentOversChart
OverCombinationsChart
Innings Details (1 column):
BowlingInningsTable
Design Tokens Reference
Import from src/theme/designSystem.js:
spacing: xs(4px), sm(8px), base(16px), lg(24px), xl(32px), section(40px)
colors: primary[600], neutral[0-950], success, warning, error
typography: fontWeight.semibold(600), fontSize.xs/sm/base
borderRadius: base(8px), lg(16px)
shadows: sm, base, md
zIndex: sticky(20), modal(30)
Apply these consistently throughout all components. -completion-promise DONE
