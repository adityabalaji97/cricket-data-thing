import React, { useState } from 'react';
import { Button, IconButton, Snackbar, Tooltip } from '@mui/material';
import IosShareRoundedIcon from '@mui/icons-material/IosShareRounded';
import { track } from '../../utils/analytics';

/**
 * Share the current page: the phone's share sheet where there is one, else copy the link.
 *
 * Every Hindsight link now unfurls with a page-specific title and preview image (api/meta.mjs,
 * api/og.mjs), so a shared link is the cheapest ad the site has. `kind` labels the share event.
 */
const ShareButton = ({ title, text, kind = 'page', variant = 'button', sx }) => {
  const [copied, setCopied] = useState(false);

  const share = async () => {
    const url = window.location.href;
    track('share', { kind });
    try {
      if (navigator.share) {
        await navigator.share({ title: title || document.title, text, url });
        return;
      }
    } catch (error) {
      if (error?.name === 'AbortError') return; // user closed the share sheet
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      // Clipboard blocked: nothing else to do.
    }
  };

  return (
    <>
      {variant === 'icon' ? (
        <Tooltip title="Share">
          <IconButton aria-label="Share this page" onClick={share} sx={sx}>
            <IosShareRoundedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      ) : (
        <Button size="small" variant="outlined" startIcon={<IosShareRoundedIcon />} onClick={share} sx={{ minHeight: 36, ...sx }}>
          Share
        </Button>
      )}
      <Snackbar
        open={copied}
        autoHideDuration={2000}
        onClose={() => setCopied(false)}
        message="Link copied"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </>
  );
};

export default ShareButton;
