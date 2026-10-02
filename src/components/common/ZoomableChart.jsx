import React, { useState } from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import ZoomOutMapIcon from '@mui/icons-material/ZoomOutMap';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';

const ZoomableChart = ({
  children,
  maxScale = 6,
  minScale = 1,
  initialScale = 1,
  isMobile = false,
}) => {
  // Pan only once zoomed in. With panning always on (and touch-action: none from the library), a
  // one-finger swipe over a scatter dragged the chart instead of scrolling the page, which
  // trapped the thumb on phones. At 1x a vertical swipe now scrolls; pinch still zooms.
  const [zoomed, setZoomed] = useState(initialScale > 1.01);
  const track = (ref, state) => setZoomed((state || ref?.state)?.scale > 1.01);

  return (
  <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
    <TransformWrapper
      initialScale={initialScale}
      minScale={minScale}
      maxScale={maxScale}
      centerOnInit
      limitToBounds
      wheel={{ step: 0.08 }}
      pinch={{ step: 5 }}
      panning={{ velocityDisabled: true, disabled: !zoomed }}
      doubleClick={{ mode: 'reset' }}
      onTransformed={track}
    >
      {({ resetTransform }) => (
        <>
          <Tooltip title="Reset zoom">
            <IconButton
              size={isMobile ? 'small' : 'medium'}
              onClick={() => resetTransform()}
              sx={{
                position: 'absolute',
                top: 8,
                right: 8,
                zIndex: 2,
                bgcolor: 'rgba(20, 23, 30, 0.92)',
                border: '1px solid',
                borderColor: 'divider',
                '&:hover': { bgcolor: 'rgba(22, 26, 34, 1)' },
              }}
            >
              <ZoomOutMapIcon fontSize={isMobile ? 'small' : 'medium'} />
            </IconButton>
          </Tooltip>
          <TransformComponent
            wrapperStyle={{ width: '100%', height: '100%', touchAction: zoomed ? 'none' : 'pan-y' }}
            contentStyle={{ width: '100%', height: '100%' }}
          >
            <Box sx={{ width: '100%', height: '100%' }}>
              {children}
            </Box>
          </TransformComponent>
        </>
      )}
    </TransformWrapper>
  </Box>
  );
};

export default ZoomableChart;

