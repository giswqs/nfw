import os
import ee
import geemap.foliumap as geemap
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

# Format a table of triplets into a 2D table of rowId x colId.


def format_table(table, rowId, colId, valueId):
    # Get a FeatureCollection with unique row IDs.
    rows = table.distinct(rowId)
    # Join the table to the unique IDs to get a collection in which
    # each feature stores a list of all features having a common row ID.
    joined = ee.Join.saveAll("matches").apply(
        **{
            "primary": rows,
            "secondary": table,
            "condition": ee.Filter.equals(**{"leftField": rowId, "rightField": rowId}),
        }
    )

    def get_value(feature):
        feature = ee.Feature(feature)
        return [feature.get(colId), feature.get(valueId)]

    def join_func(row):
        values = ee.List(row.get("matches")).map(get_value)
        # Map a function over the list of rows to return a list of
        # column ID and value. \
        return row.select([rowId]).set(ee.Dictionary(values.flatten()))

    return joined.map(join_func)


def wetland_mapping(
    Map,
    output,
    watershed,
    selected_year,
    cluster_threshold,
    permanent_threshold,
    usda_threshold,
):

    # Customize parameters
    # watershed:           HUC10 watershed ID
    # selected_year:       selected year to display NAIP imagery
    # nclusters:           number of clusters for the k-means clustering
    # cluster_threshold:   A cluster within permanent water must exceed x% of pixels in order to be classified as water
    # permanent_threshold: threshold (%) for extracting permanent water from JRC Global Water Occurrence
    # usda_threshold:      usda cropland water threshold 1-21.

    huc8_id = watershed[0:8]
    # Available 4-band NAIP imagery
    years = [2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019]
    num_years = len(years)  # number of years with available NAIP imagery

    basin_fc = geemap.find_HUC10(watershed)
    basin_geom = basin_fc.geometry()
    basin_name = basin_fc.first().get("name")
    basin_size = basin_geom.area().divide(1e4).format("%.4f")

    # Get time-series NAIP imagery with NDWI and NDVI bands added
    NAIP_images = geemap.find_NAIP(basin_fc)
    with output:
        st.write("Running. Please wait ...")

    # image acquisition date (starting time)
    time_start = ee.List(NAIP_images.aggregate_array("system:time_start"))
    # image acquisition date (ending time)
    time_end = ee.List(NAIP_images.aggregate_array("system:time_end"))
    yearList = time_start.map(lambda y: ee.Date(y).get("year"))

    ith_year_tmp = yearList.indexOf(selected_year)
    print(ith_year_tmp.getInfo())
    ith_year = ee.List([ith_year_tmp, 0]).reduce(ee.Reducer.max())
    shown_year = yearList.get(ith_year).getInfo()
    # selected NAIP imagery to display on the map
    ith_NAIP = ee.Image(NAIP_images.toList(num_years).get(ith_year))

    # image = ee.Image(NAIP_images.toList(NAIP_images.size()).get(ith_year))
    # Map.layers = Map.layers[:5]
    layer_name = "NAIP " + ith_NAIP.get("system:time_start").getInfo()
    #     Map.centerObject(basin_geom, 11)
    Map.addLayer(ith_NAIP, {"bands": ["N", "R", "G"]}, layer_name)

    # get NED and landforms
    elev = ee.Image("USGS/NED").clip(basin_geom)
    hillshade = ee.Terrain.hillshade(elev)
    landforms = (
        ee.Image("CSP/ERGo/1_0/US/landforms").select("constant").clip(basin_geom).byte()
    )
    # including upper slope (flat), lower slope, valley
    landforms_wet = landforms.gt(23).selfMask()

    # Get waters and wetlands from USDA Cropland data layer
    # https://developers.google.com/earth-engine/datasets/catalog/USDA_NASS_CDL

    def get_usda_waters(geometry, usda_water_threshold):
        cropland = (
            ee.ImageCollection("USDA/NASS/CDL")
            .filterDate("1997-01-01", "2019-12-31")
            .select("cropland")
        )
        usda_waters = cropland.map(
            lambda img: img.remap([83, 87, 111, 190, 195], ee.List.repeat(999, 5))
            .eq(999)
            .clip(geometry)
            .selfMask()
        )
        usda_water_occurrence = usda_waters.reduce(ee.Reducer.sum()).selfMask()
        usda_water_extent = usda_water_occurrence.gt(usda_water_threshold).selfMask()
        return usda_water_occurrence, usda_water_extent

    usda_occurrence, usda_max_extent = get_usda_waters(basin_geom, usda_threshold)

    # Get NLCD land cover 1992, 2001, 2004, 2006, 2008, 2011, 2013, 2016
    def get_nlcd(geometry, nlcd_water_threshold):

        landcover = (
            ee.ImageCollection("USGS/NLCD")
            .filterBounds(geometry)
            .select("landcover")
            .map(lambda x: x.clip(geometry))
        )
        nlcd_waters = landcover.map(
            lambda img: img.remap([11, 90, 95], ee.List.repeat(99, 3))
            .eq(99)
            .clip(geometry)
            .selfMask()
        )
        nlcd_water_occurrence = nlcd_waters.reduce(ee.Reducer.sum()).selfMask()
        nlcd_water_extent = nlcd_water_occurrence.gt(nlcd_water_threshold).selfMask()
        return landcover, nlcd_water_occurrence, nlcd_water_extent

    nlcd_landcover, nlcd_occurrence, nlcd_max_extent = get_nlcd(
        basin_geom, usda_threshold
    )
    nlcd_2016 = ee.Image(nlcd_landcover.toList(nlcd_landcover.size()).get(-1))

    # JRC Global Surface Water Mapping Layers (1984-2019)
    JRC_Water = ee.Image("JRC/GSW1_2/GlobalSurfaceWater").clip(basin_geom)
    # Binary image containing 1 anywhere water has ever been detected.
    JRC_Water_Max_Extent = JRC_Water.select("max_extent")
    JRC_Water_Occurrence = JRC_Water.select("occurrence")
    JRC_Permanent_Water = JRC_Water_Occurrence.gt(permanent_threshold)
    JRC_Permanent_Water = JRC_Permanent_Water.selfMask()

    # NWI wetlands for the clicked watershed
    nwi_asset_path = "users/giswqs/NWI-HU8/HU8_" + huc8_id + "_Wetlands"
    basin_nwi = ee.FeatureCollection(nwi_asset_path).filterBounds(basin_geom)
    #     print(basin_nwi.first().getInfo())
    #     print(basin_nwi.aggregate_stats('Shape_Area').getInfo())
    nwi_color = geemap.nwi_add_color(basin_nwi)

    # extract JRC Monthly History product
    def get_JRC_monthly(img):
        start_date = ee.Date(img.get("system:time_start"))
        end_date = ee.Date(img.get("system:time_end"))
        start_year_tmp = ee.Number(start_date.get("year"))
        start_year = ee.List([start_year_tmp, 2019]).reduce(ee.Reducer.min())
        # Between 16 March 1984 and 31 December 2019
        start_month = ee.Number(start_date.get("month"))
        end_month = ee.Number(end_date.get("month")).add(1)
        start = ee.Date.fromYMD(start_year, start_month, 1)
        end = start.advance(59, "day")
        JRC_monthly_images = ee.ImageCollection("JRC/GSW1_2/MonthlyHistory").filterDate(
            start, end
        )
        JRC_monthly_size = ee.Number(JRC_monthly_images.size())
        alt_start = ee.Date.fromYMD(2019, start_month, 1)
        alt_end = alt_start.advance(59, "day")
        alt_JRC_monthly_images = ee.ImageCollection(
            "JRC/GSW1_2/MonthlyHistory"
        ).filterDate(alt_start, alt_end)
        JRC_monthly_images = ee.ImageCollection(
            ee.Algorithms.If(
                JRC_monthly_size.gt(0), JRC_monthly_images, alt_JRC_monthly_images
            )
        )
        # JRC_monthly = JRC_monthly_images.max().eq(2).clip(getImageBound(img))
        JRC_monthly = JRC_monthly_images.max().eq(2).clip(basin_geom).selfMask()
        # JRC_monthly = JRC_monthly.updateMask(JRC_monthly)
        return JRC_monthly.set({"system:time_start": start, "system:time_end": end})

    #     # extract JRC Monthly History product
    #     def get_JRC_monthly(img):
    #         start_date = ee.Date(img.get('system:time_start'))
    #         end_date = ee.Date(img.get('system:time_end'))
    #         start_year = ee.Number(start_date.get('year'))
    #         start_month = ee.Number(start_date.get('month'))
    # #         end_month = ee.Number(end_date.get('month')).add(1)
    #         start = ee.Date.fromYMD(start_year, start_month, 1)
    #         end = start.advance(1, 'month')
    #         JRC_monthly_images = ee.ImageCollection("JRC/GSW1_2/MonthlyHistory").filterDate(start, end)
    #         JRC_monthly = JRC_monthly_images.max().clip(basin_geom).selfMask()
    #         return JRC_monthly

    JRC_monthly_waters = NAIP_images.map(get_JRC_monthly)
    #     print(JRC_monthly_waters.getInfo())
    ith_JRCwater = ee.Image(JRC_monthly_waters.toList(num_years).get(ith_year))

    centroid = ee.FeatureCollection.randomPoints(basin_geom, 1).first().geometry()
    lon = centroid.coordinates().get(0)
    # deal with points near the US/Canada border
    lat_tmp = centroid.coordinates().get(1)
    lat = ee.List([lat_tmp, 48.998]).reduce(ee.Reducer.min())
    centroid = ee.Geometry.Point([lon, lat])
    cls_roi = centroid.buffer(5000)

    # function for classifying image using k-means clustering
    def classify_image(img):

        training = img.sample(
            **{
                "region": cls_roi,  # using the sample image to extract training samples
                "scale": 2,
                "numPixels": 5000,
            }
        )
        # Instantiate the clusterer and train it.
        # clusterer = ee.Clusterer.wekaKMeans(nclusters).train(training)
        clusterer = ee.Clusterer.wekaXMeans().train(training)
        # Cluster the img using the trained clusterer.
        classified_image = img.cluster(clusterer).select("cluster")
        return classified_image

    # classifying the image collection using the map function
    cluster_images = NAIP_images.map(classify_image)
    ith_cluster_image = ee.Image(
        cluster_images.toList(num_years).get(ith_year)
    )  # selected year of image to display on the map

    def get_water_cluster(img):
        cluster_img = img.updateMask(JRC_Permanent_Water)
        frequency = cluster_img.reduceRegion(
            **{
                "reducer": ee.Reducer.frequencyHistogram(),
                "scale": 30,
                "maxPixels": 2.1e9,
            }
        )
        cluster_dict = ee.Dictionary(frequency.get("cluster"))
        keys = ee.List(cluster_dict.keys())
        # print(keys.getInfo())
        values = ee.List(cluster_dict.values())
        threshold = ee.Number(values.reduce(ee.Reducer.sum())).multiply(
            cluster_threshold
        )
        # make sure each cluster > 10% * sum
        threshold = ee.List([threshold, 5000]).reduce(ee.Reducer.min())
        clusterList = values.map(lambda value: ee.Number(value).gt(threshold))

        indexes = ee.List.sequence(0, keys.size().subtract(1))
        clsLabels = indexes.map(
            lambda index: ee.Number.parse((keys.get(index)))
            .add(1)
            .multiply(clusterList.get(index))
        )
        clsLabels = clsLabels.removeAll(ee.List([0]))
        clsLabels = clsLabels.map(lambda x: ee.Number(x).subtract(1))
        outList = ee.List.repeat(-1, clsLabels.size())
        cluster_img = img.remap(clsLabels, outList).eq(-1)
        cluster_img = cluster_img.updateMask(cluster_img)
        return cluster_img

    # ithClusterImg = getWaterCluster(ithClusterImage)
    water_images = cluster_images.map(get_water_cluster)
    ith_water_image = ee.Image(water_images.toList(num_years).get(ith_year))

    # Water regions must reside within USDA max water extent
    def refine_water(img):
        return img.And(usda_max_extent).And(water_images.sum().gt(1)).selfMask()

    refined_images = water_images.map(refine_water)

    occurrence = ee.Image(refined_images.sum().toUint8())

    # add image date to resulting image based on the original NAIP image
    def add_date(img):
        sys_index = ee.Number.parse(img.get("system:index"))
        start_index = time_start.get(sys_index)
        end_index = time_end.get(sys_index)
        return img.set({"system:time_start": start_index, "system:time_end": end_index})

    refined_images = refined_images.map(add_date)
    ith_refined_water = ee.Image(refined_images.toList(num_years).get(ith_year))

    # calculate omission error
    def calcOmission(img):
        sys_index = ee.Number.parse(img.get("system:index"))
        iJRCwater = ee.Image(JRC_monthly_waters.toList(num_years).get(sys_index))
        inputUnmask = img.unmask()
        omissionImage = inputUnmask.eq(0).And(iJRCwater.eq(1))
        omissionImage = omissionImage.selfMask()
        return omissionImage

    omission_images = refined_images.map(calcOmission)
    omission_images = omission_images.map(add_date)

    # calculate pixel area in hectare
    def get_area(img):
        pixelArea = img.multiply(ee.Image.pixelArea()).divide(10000)
        watershedArea = pixelArea.reduceRegions(
            **{"collection": basin_fc, "reducer": ee.Reducer.sum(), "scale": 10}
        )

        def set_year(fc):
            year = ee.Date(img.get("system:time_start")).get("year")
            fieldValue = ee.String("Y").cat(ee.String(year.format()))
            return fc.set("year", fieldValue)

        watershedArea = watershedArea.map(set_year)
        watershedArea = watershedArea.select(["huc10", "name", "year", "sum"])
        return watershedArea  # .select([".*"], None, False)

    NAIP_water_areas = refined_images.map(get_area)
    NAIP_water_areas = NAIP_water_areas.flatten()

    JRC_water_areas = JRC_monthly_waters.map(get_area)
    JRC_water_areas = JRC_water_areas.flatten()

    x = list(NAIP_water_areas.aggregate_array("year").getInfo())
    labels = [i[1:] for i in x]

    y = list(NAIP_water_areas.aggregate_array("sum").getInfo())
    y = [round(i, 2) for i in y]
    y2 = list(JRC_water_areas.aggregate_array("sum").getInfo())
    y2 = [round(i, 2) for i in y2]

    fig, ax = plt.subplots()
    x = np.arange(len(labels))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots()
    fig.set_size_inches(10, 6)
    rects1 = ax.bar(x - width / 2, y, width, label="NAIP")
    rects2 = ax.bar(x + width / 2, y2, width, label="JRC")

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel("Area (ha)")
    ax.set_title("Inundation dynamics")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    ax.bar_label(rects1, padding=3)
    ax.bar_label(rects2, padding=3)
    plt.margins(y=0.2, tight=True)

    # fig.tight_layout()

    # with output:
    #     st.pyplot(fig)

    # fig = plt.figure(1)
    # fig.layout.height = "280px"
    # plt.clear()
    #     plt.bar(x, y)
    # bar_chart = plt.bar(x, [y, y2], labels=[
    #                     "NAIP", "JRC"], display_legend=True)
    # plt.title("Inundation dynamics")
    # plt.xlabel("Year")
    # plt.ylabel("Area (ha)")
    # bar_chart.colors = ["blue", "tomato"]
    # bar_chart.type = "grouped"
    # bar_chart.tooltip = Tooltip(fields=["x", "y"], labels=["Year", "NAIP/JRC"])
    # # output.clear_output()
    # plt.show()
    # print("Exporting data ...")

    omission_areas = omission_images.map(get_area)
    omission_areas = omission_areas.flatten()

    NAIP_water_table = ee.FeatureCollection(
        format_table(NAIP_water_areas, "name", "year", "sum")
    )
    JRC_water_table = ee.FeatureCollection(
        format_table(JRC_water_areas, "name", "year", "sum")
    )
    omission_table = ee.FeatureCollection(
        format_table(omission_areas, "name", "year", "sum")
    )

    #     NAIP_water_table = NAIP_water_table.map(lambda f: f.set({'Type': 'NAIP'}))
    #     JRC_water_table = JRC_water_table.map(lambda f: f.set({'Type': 'JRC'}))
    #     omission_table = omission_table.map(lambda f: f.set({'Type': 'Omission'}))

    #     NAIP_water_table = geemap.remove_geometry(NAIP_water_table)
    #     JRC_water_table = geemap.remove_geometry(JRC_water_table)
    #     omission_table = geemap.remove_geometry(omission_table)
    stats_table = NAIP_water_table.merge(JRC_water_table).merge(omission_table)
    #     print(stats_table.getInfo())

    #     NWI_summary = geemap.summary_stats(basin_nwi, 'Shape_Area')
    NWI_summary = eval(str(basin_nwi.aggregate_stats("Shape_Area").getInfo()))
    #     print(NWI_summary)
    NWI_count = NWI_summary.get("total_count")
    NWI_total = "{:.4f}".format(NWI_summary.get("sum") / 10000)
    NWI_mean = "{:.4f}".format(NWI_summary.get("mean") / 10000)
    NWI_min = "{:.4f}".format(NWI_summary.get("min") / 10000)
    NWI_max = "{:.4f}".format(NWI_summary.get("max") / 10000)
    NWI_median = ee.Dictionary(
        geemap.column_stats(basin_nwi, "Shape_Area", "median")
    ).get("median")
    NWI_median = geemap.ee_num_round(ee.Number(NWI_median).divide(10000), 4)

    NWI_dict = ee.Dictionary(
        {
            "NWI_count": NWI_count,
            "NWI_sum": NWI_total,
            "NWI_mean": NWI_mean,
            "NWI_median": NWI_median,
            "NWI_min": NWI_min,
            "NWI_max": NWI_max,
        }
    )
    #     print(NWI_dict.getInfo())

    # Aggregated wetland area for each wetland type
    NWI_sums = geemap.summarize_by_group(
        basin_nwi, "Shape_Area", "WETLAND_TY", "Wetland Type", "sum"
    )
    NWI_sums = NWI_sums.rename(NWI_sums.keys(), geemap.nwi_rename(NWI_sums.keys()))
    NWI_sums = NWI_sums.rename(
        NWI_sums.keys(),
        NWI_sums.keys().map(lambda k: ee.String("NWI_").cat(ee.String(k))),
    )
    NWI_sums = ee.Dictionary.fromLists(
        NWI_sums.keys(),
        NWI_sums.values().map(
            lambda v: ee.Number.parse(ee.Number(v).divide(10000).format("%.4f"))
        ),
    )
    NWI_dict = NWI_dict.combine(NWI_sums)
    #     print(NWI_dict.getInfo())

    #     NWI_medians = geemap.summarize_by_group(basin_nwi, 'Shape_Area', 'WETLAND_TY', 'Wetland Type', 'median')
    #     NWI_medians = NWI_medians.rename(NWI_medians.keys(), geemap.nwi_rename(NWI_medians.keys()))
    #     NWI_medians = NWI_medians.rename(NWI_medians.keys(), NWI_medians.keys().map(lambda k: ee.String('Median-').cat(ee.String(k))))
    #     print(NWI_medians.getInfo())

    #     NWI_median = geemap.column_stats(basin_nwi, 'Shape_Area', 'median')
    #     NWI_median = NWI_median.rename(NWI_median.keys(),
    #                                    NWI_median.keys().map(lambda k: ee.String(k).replace('median', 'NWI-median')))
    #     print(NWI_median.getInfo())

    def pre_data_dict(fc):
        fc_dict = fc.first().toDictionary().remove(["name"])
        fc_dict_keys = fc_dict.keys()
        fc_dict_values = fc_dict_keys.map(
            lambda key: ee.Number.parse(ee.Number(fc_dict.get(key)).format("%.2f"))
        )
        fc_dict = ee.Dictionary.fromLists(fc_dict_keys, fc_dict_values)
        return fc_dict

    JRC_dict = pre_data_dict(JRC_water_table)
    NAIP_dict = pre_data_dict(NAIP_water_table)
    OMI_dict = pre_data_dict(omission_table)

    JRC_dict = JRC_dict.rename(
        JRC_dict.keys(),
        JRC_dict.keys().map(lambda k: ee.String(k).replace("Y", "JRC_")),
    )
    NAIP_dict = NAIP_dict.rename(
        NAIP_dict.keys(),
        NAIP_dict.keys().map(lambda k: ee.String(k).replace("Y", "NAIP_")),
    )
    OMI_dict = OMI_dict.rename(
        OMI_dict.keys(),
        OMI_dict.keys().map(lambda k: ee.String(k).replace("Y", "OMI_")),
    )

    def create_data_dict():
        data = ee.Dictionary(
            {
                "HUC_10": watershed,
                "HUC_08": huc8_id,
                "HUC_Name": basin_name,
                "HUC_Area": basin_size,
            }
        )
        data = (
            data.combine(JRC_dict)
            .combine(NAIP_dict)
            .combine(OMI_dict)
            .combine(NWI_dict)
        )
        return data

    data_dict = create_data_dict()
    #     print(data_dict.getInfo())
    csv_feature = ee.Feature(None, data_dict)
    csv_feat_col = ee.FeatureCollection([csv_feature])
    #     print(csv_feat_col.getInfo())
    #     out_csv = os.path.join(os.path.expanduser('~/Downloads'), watershed + '.csv')
    #     geemap.ee_export_vector(csv_feat_col, out_csv)
    #     link = geemap.create_download_link(out_csv)
    #     display(link)
    # Map.addLayer(ith_NAIP, vis_naip, 'NAIP-' + str(selected_year))
    #     Map.addLayer(hillshade, {}, 'NED Hillshade', False)
    #     Map.addLayer(landforms, vis_landform, 'NED Landforms', False)
    #     Map.addLayer(nlcd_2016, {}, "NLCD 2016", False)
    Map.addLayer(ith_cluster_image.randomVisualizer(), {}, "X-Means Clusters", False)
    Map.addLayer(occurrence.randomVisualizer(), {}, "NAIP Water Occurrence")
    #     Map.addLayer(ith_water_image, {'palette': 'white'}, 'Water Clusters', False)
    #     Map.addLayer(landforms_wet, {'palette': 'cyan'}, 'NED Wet Landforms', False)
    #     Map.addLayer(usda_occurrence, vis_cropland, 'USDA Water Occurrence', False)
    #     Map.addLayer(usda_max_extent, {}, 'USDA Max Water Extent', False)
    #     Map.addLayer(nlcd_occurrence.randomVisualizer(), {}, 'NLCD Water Occurrence', False)
    #     Map.addLayer(nlcd_max_extent, {}, 'NLCD Max Water Extent', False)
    #     Map.addLayer(JRC_Water_Occurrence, vis_ndwi, 'JRC Water Occurrence')
    Map.addLayer(
        ith_JRCwater,
        {"palette": "orange"},
        "JRC Inundation Area ({})".format(shown_year),
        False,
    )
    Map.addLayer(
        ith_refined_water,
        {"palette": "blue"},
        "NAIP Inundation Area ({})".format(shown_year),
    )
    Map.centerObject(basin_fc, 10)
    #     Map.addLayer(JRC_Permanent_Water, {'palette': 'white'}, "JRC Permanent Water", False)
    # Map.addLayer(nwi_color, {'gamma': 0.3, 'opacity': 0.7}, 'NWI Wetlands Color', False)
    #     Map.add_basemap('FWS NWI Wetlands')
    #     Map.add_legend(builtin_legend='NWI')
    # return csv_feat_col
    return fig


def app():

    st.title("Surface Water Mapping Using NAIP Imagery")
    in_csv = os.path.join(os.path.dirname(__file__), "data/WBDHU10.csv")
    with open(in_csv) as f:
        hu10_list = f.readlines()[1:]

    Map = geemap.Map(plugin_Draw=True, Draw_export=True)
    with st.form(key="submit_form"):

        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 2, 0.2, 1, 1])
        selected = col1.selectbox("Select a HU10", hu10_list, index=3547)
        lat = col2.text_input("Enter a latitude", "")
        lon = col3.text_input("Enter a longitude", "")
        year = col4.slider("Select a year to display NAIP imagery", 2008, 2019, 2019)

        submit = st.form_submit_button(label="Submit")

    output = st.empty()

    if submit:
        output.write("Running. Please wait ...")
        fig = wetland_mapping(Map, output, selected.strip(), year, 0.1, 30, 2)
        with output.expander("See chart"):
            st.pyplot(fig)
        # output.pyplot(fig)

    # Load Prairie Pothole Region (PPR) and National Hydrography Dataset (NHD)
    # Map.add_basemap('HYBRID')
    ROI = ee.FeatureCollection("users/giswqs/MRB/NWI_HU8_Boundary_Simplify")

    # Map.setCenter(-103.840563, 45.397968, 6)

    # 18,487 HUC10 watersheds in the U.S.
    # HUC10 = ee.FeatureCollection("USGS/WBD/2017/HUC10")
    # # 2,303 HUC08 subbasins in the U.S.
    # HUC08 = ee.FeatureCollection('USGS/WBD/2017/HUC08')
    # # 993 HUC10 watersheds in the PPR
    # PPR_HUC10 = HUC10.filterBounds(ROI)
    # # 132 HUC08 subbasins in the PPR
    # PPR_HUC08 = HUC08.filterBounds(ROI)

    # ROI_HUC10 = HUC10.filterBounds(ROI)
    # ROI_HUC10_style = ROI_HUC10.style(
    #     **{"color": "000000", "width": 1, "fillColor": "00000000"}
    # )
    # Map.addLayer(ROI_HUC10_style, {}, "PPR HUC10 Watershed")  # HUC10 for the PPR

    huc8 = ee.FeatureCollection("USGS/WBD/2017/HUC10").filter(
        ee.Filter.Or(
            ee.Filter.stringStartsWith(**{"leftField": "huc10", "rightValue": "05"}),
            ee.Filter.stringStartsWith(**{"leftField": "huc10", "rightValue": "07"}),
            ee.Filter.stringStartsWith(**{"leftField": "huc10", "rightValue": "10"}),
        )
    )
    Map.addLayer(huc8.style(**{"fillColor": "00000000", "width": 1}), {}, "NHD-HUC10")
    ROI_style = ROI.style(**{"color": "0000FF", "width": 2, "fillColor": "00000000"})
    Map.addLayer(ROI_style, {}, "MRB")
    Map.to_streamlit(width=1400, height=700)

    with col6:
        st.write(f"Number of HU10: 4600")
