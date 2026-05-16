import unittest
import unittest.mock as mock

from mwclient.client import Site, WikiBaseSite
from mwclient.entity import GlobeCoordinate, Item, Property
from mwclient.page import Page


def make_mock_wikibase_site(host: str = "www.wikidata.org") -> mock.MagicMock:
    site = mock.MagicMock()
    site.host = host
    return site


class TestPageWikibaseItem(unittest.TestCase):

    @mock.patch('mwclient.client.Site')
    def test_wikibase_item_returns_item(self, MockSite):
        site = MockSite()
        site.get.return_value = {
            "query": {
                "pages": {
                    "1": {
                        "title": "Paris",
                        "ns": 0,
                        "pageid": 1}}}}
        page = Page(site, "Paris")
        site.api.return_value = {
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "pageprops": {"wikibase_item": "Q90"}}}}
        }
        site.wikibase_repository = make_mock_wikibase_site()
        assert isinstance(page.wikibase_item, Item)
        assert page.wikibase_item.entity == "Q90"


class TestWikiBaseSiteRepr(unittest.TestCase):

    def test_repr(self):
        with mock.patch.object(WikiBaseSite, '__init__', lambda self, *a, **kw: None):
            site = WikiBaseSite.__new__(WikiBaseSite)
            site.host = "www.wikidata.org"
            site.path = "/w/"
        assert repr(site) == "<WikiBaseSite object 'www.wikidata.org/w/'>"


class TestItemClaims(unittest.TestCase):

    def setUp(self):
        self.site = make_mock_wikibase_site()
        self.site.api.return_value = {
            "claims": {
                "P625": [
                    {
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P625",
                            "datatype": "globe-coordinate",
                            "datavalue": {
                                "value":{
                                    "latitude": 48.86,
                                    "longitude": 2.35,
                                    "altitude": None,
                                    "precision": 0.0001,
                                    "globe":
                                        "http://www.wikidata.org/entity/Q2"
                                    }},}}],
                "P150": [
                    {
                        "mainsnak": {
                        "snaktype": "value",
                        "property": "P150",
                        "datatype": "wikibase-item",
                        "datavalue":{
                            "value": {
                                "numeric-id": 75056,
                                "entity-type": "item"}},}}],
            }
        }
        self.item = Item(self.site, "Q90")

    def test_claims_returns_all(self):
        assert len(self.item.claims()) == 2

    def test_claims_filter_by_prop_coordinates(self):
        coords = self.item.claims(prop=["P625"])
        assert len(coords) == 1
        coord = coords[0].value
        assert isinstance(coord, GlobeCoordinate)
        assert coord.latitude == 48.86
        assert coord.longitude == 2.35

    def test_claims_filter_by_prop_item(self):
        subdivisions = self.item.claims(prop=["P150"])
        assert len(subdivisions) == 1
        assert isinstance(subdivisions[0].value, Item)


class TestWikiBaseSiteEntities(unittest.TestCase):

    def setUp(self):
        with mock.patch.object(WikiBaseSite, '__init__', lambda self, *a, **kw: None):
            self.site = WikiBaseSite.__new__(WikiBaseSite)
            self.site.host = "www.wikidata.org"
        patcher = mock.patch.object(self.site, 'api', mock.MagicMock(return_value={
            "entities": {
                "Q42": {
                    "type": "item",
                    "labels": {},
                    "descriptions": {},
                    "sitelinks": {},
                    "claims": {}},
                "P238": {
                    "type": "property",
                    "labels": {},
                    "descriptions": {},
                    "sitelinks": {},
                    "claims": {}},
            }
        }))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_entities_returns_mixed_items_and_properties(self):
        entities = self.site.entities(ids=["Q42", "P238"])
        assert len(entities) == 2
        assert {type(e) for e in entities} == {Item, Property}

    def test_item_repr(self):
        entities = self.site.entities(ids=["Q42", "P238"])
        item = next(e for e in entities if isinstance(e, Item))
        assert repr(item) == "<Item object Q42 (www.wikidata.org)>"

    def test_property_repr(self):
        entities = self.site.entities(ids=["Q42", "P238"])
        prop = next(e for e in entities if isinstance(e, Property))
        assert repr(prop) == "<Property object P238 (www.wikidata.org)>"

    def test_property_claims_filtered(self):
        prop_site = make_mock_wikibase_site()
        prop_site.api.return_value = {
            "claims": {
                "P1659": [
                    {
                        "mainsnak": {
                            "snaktype": "value",
                            "property":
                            "P1659",
                            "datatype": "wikibase-property",
                            "datavalue": {
                                "value":{
                                    "numeric-id": 239,
                                    "entity-type": "property"}}}},
                    {
                        "mainsnak": {
                            "snaktype":
                            "value",
                            "property":
                            "P1659",
                            "datatype": "wikibase-property",
                            "datavalue": {
                                "value": {
                                    "numeric-id": 229,
                                    "entity-type": "property"}}}},
                ],
            }
        }
        prop = Property(prop_site, "P238")
        related = prop.claims(prop=["P1659"])
        assert len(related) == 2
        assert all(isinstance(c.value, Property) for c in related)


class TestSiteWikibaseRepository(unittest.TestCase):

    def setUp(self):
        self.site = Site('www.wikipedia.org', do_init=False, pool=mock.MagicMock())
        self.mock_api = mock.MagicMock(return_value={
            "query": {"wikibase": {"repo": {"url": {
                "base": "https://www.wikidata.org",
                "scriptpath": "/w"
            }}}}
        })
        patcher = mock.patch.object(self.site, 'api', self.mock_api)
        patcher.start()
        self.addCleanup(patcher.stop)

    @mock.patch('mwclient.client.WikiBaseSite')
    def test_wikibase_repository_returns_wikibase_site(self, MockWikiBaseSite):
        repo = self.site.wikibase_repository
        MockWikiBaseSite.assert_called_once_with(
            "www.wikidata.org", path="/w/", scheme="https", pool=self.site.connection
        )
        assert repo is MockWikiBaseSite.return_value

    @mock.patch('mwclient.client.WikiBaseSite')
    def test_wikibase_repository_is_cached(self, MockWikiBaseSite):
        repo1 = self.site.wikibase_repository
        repo2 = self.site.wikibase_repository
        assert repo1 is repo2
        self.mock_api.assert_called_once()


if __name__ == "__main__":
    unittest.main()
