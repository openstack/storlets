/*----------------------------------------------------------------------------
 * Copyright IBM Corp. 2015, 2015 All Rights Reserved
 * Copyright 2016 OpenStack Foundation
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * Limitations under the License.
 * ---------------------------------------------------------------------------
 */
package org.openstack.storlet.thumbnail;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.io.InputStream;
import java.io.OutputStream;

import org.openstack.storlet.common.IStorlet;
import org.openstack.storlet.common.StorletException;
import org.openstack.storlet.common.StorletInputStream;
import org.openstack.storlet.common.StorletLogger;
import org.openstack.storlet.common.StorletObjectOutputStream;
import org.openstack.storlet.common.StorletContainerHandle;
import org.openstack.storlet.common.StorletOutputStream;
import org.openstack.storlet.common.StorletUtils;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.awt.Image;
import java.awt.Transparency;
import java.awt.Graphics2D;
import java.awt.RenderingHints;

public class ThumbnailStorlet implements IStorlet {
    @Override
    public void invoke(ArrayList<StorletInputStream> inputStreams,
            ArrayList<StorletOutputStream> outputStreams,
            Map<String, String> parameters, StorletLogger log)
            throws StorletException {
        log.emitLog("ThumbnailStorlet Invoked");

        /*
         * Get input stuff
         */
        HashMap<String, String> object_md;
        StorletInputStream storletInputStream = inputStreams.get(0);
                InputStream thumbnailInputStream = storletInputStream.getStream();
        object_md = storletInputStream.getMetadata();
        /*
         * Get output stuff
         */

        StorletObjectOutputStream storletObjectOutputStream = (StorletObjectOutputStream)outputStreams.get(0);
                OutputStream thumbnailOutputStream = storletObjectOutputStream.getStream();

        /*
         * Set the output metadata
         */
        log.emitLog("Setting metadata");
        storletObjectOutputStream.setMetadata(object_md);

        /*
         * Read Input to BufferedImage
         */
        log.emitLog("Reading Input");
        BufferedImage img = null;
                try {
                img = ImageIO.read(thumbnailInputStream);
        } catch (Exception e) {
            log.emitLog("Failed to read input stream to buffered image");
            throw new StorletException("Failed to read input stream to buffered image " + e.getMessage());
        } finally {
            try {
                thumbnailInputStream.close();
            } catch (IOException e) {
                log.emitLog("Failed to close input stream");
            }
        }
        try {
            thumbnailInputStream.close();
        } catch (IOException e) {
            log.emitLog("Failed to close input stream");
        }

        /*
         * Convert
         */
        log.emitLog("Converting");
        int newH = img.getHeight()/8;
        int newW = img.getWidth()/8;
                int type = img.getTransparency() == Transparency.OPAQUE ? BufferedImage.TYPE_INT_RGB : BufferedImage.TYPE_INT_ARGB;
        BufferedImage thumbnailImage = new BufferedImage(newW, newH, type);
                Graphics2D g = thumbnailImage.createGraphics();
                g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
                g.drawImage(img, 0, 0, newW, newH, null);
                g.dispose();

        /*
         * Write
         */
        log.emitLog("Writing Output");
        try {
            ImageIO.write(thumbnailImage, "PNG" , thumbnailOutputStream);
        } catch (Exception e) {
            log.emitLog("Failed to write image to out stream");
            throw new StorletException("Failed to write image to out stream " + e.getMessage());
        } finally {
            try {
                thumbnailOutputStream.close();
            } catch (IOException e) {
            }
        }

        try {
                thumbnailOutputStream.close();
        } catch (IOException e) {
        }

        log.emitLog("Done");

    }
}
