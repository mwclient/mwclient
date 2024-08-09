"""WikiBase Entities and related objects."""


class Entity(object):

    """Wikibase Entity, either Item or Property.

    This class should not be implemented directly,
    It is meant to be abstract for Item and Property.

    Attributes:
        site (WikiBaseSite): reference to a WikiBaseSite
        entity (str): Q number of the entity.
        descriptions (dict): dictionary containing description per language
        labels (dict): dictionary containing labels per language
    """

    def __init__(self, site, normalized_entity):
        """Common part of constructor for Item and Property."""
        self.site = site

        self.entity = normalized_entity
        # caching descriptions, labels, sitelinks
        # self._sitelinks = None
        self._descriptions = None
        self._labels = None

        # caching claims
        self._itemclaims = None

    def setinfofromwbgetentities(self, result):
        """Set descriptions, labels and claims from wbgetentities result."""
        self._descriptions = dict()
        for language in result['descriptions']:
            lang = result['descriptions'][language]['language']
            value = result['descriptions'][language]['value']
            self._descriptions[lang] = value
        self._labels = dict()
        for language in result['labels']:
            lang = result['labels'][language]['language']
            value = result['labels'][language]['value']
            self._labels[lang] = value
        if self._itemclaims is None:
            self._itemclaims = []
            for prop in result['claims']:
                for claim in result['claims'][prop]:
                    mainsnak = claim['mainsnak']
                    self._itemclaims.append(Claim.fromsnak(self.site,
                                                           mainsnak))

    @property
    def labels(self):
        """Labels dictionary per language"""
        if self._labels is None:
            entities = self.site.api('wbgetentities', ids=self.entity)
            result = entities['entities'][self.entity]
            self.setinfofromwbgetentities(result)
        return self._labels

    @property
    def descriptions(self):
        """Descriptions dictionary per language"""
        if self._descriptions is None:
            entities = self.site.api('wbgetentities', ids=self.entity)
            result = entities['entities'][self.entity]
            self.setinfofromwbgetentities(result)
        return self._descriptions

    def claims(self, prop=None):
        """Claims about an Entity.

        API Doc: https://www.mediawiki.org/wiki/Wikibase/API/en#wbgetclaims
        We will probably need to implement rank and props later on.

        Args:
            prop (list, optional): list of property e.g. ['P238', 'P239']
        """
        if self._itemclaims is None:
            self._itemclaims = []
            info = self.site.api('wbgetclaims', entity=self.entity)['claims']

            for propid in info:
                for claim in info[propid]:
                    mainsnak = claim['mainsnak']
                    self._itemclaims.append(Claim.fromsnak(self.site,
                                                           mainsnak))
        if prop is None:
            return self._itemclaims
        else:
            return [claim for claim in self._itemclaims if claim.prop in prop]


class Item(Entity):

    """Wikibase Item.

    Attributes:
        site (WikiBaseSite): reference to a WikiBaseSite
        entity (str): Q number of the entity.
        sitelinks (dict): dictionary containing sitelinks per wiki
        descriptions (dict): dictionary containing description per language
        labels (dict): dictionary containing labels per language
    """

    def __init__(self, site, entity):
        """Constructor.

        Args:
            site (WikiBaseSite): reference to a WikiBaseSite
            entity (str): Q number of the entity.
        """
        # Normalizing entity name
        super(Item, self).__init__(site, 'Q' + entity.upper().lstrip('Q'))

        self._sitelinks = None

    def setinfofromwbgetentities(self, result):
        """Set sitelinks, descriptions, labels, claims from wbgetentities."""
        super(Item, self).setinfofromwbgetentities(result)
        self._sitelinks = dict()
        for wiki in result['sitelinks']:
            site = result['sitelinks'][wiki]['site']
            title = result['sitelinks'][wiki]['title']
            badges = result['sitelinks'][wiki]['badges']
            self._sitelinks[site] = {'title': title, 'badges': badges}

    @property
    def sitelinks(self):
        """Sitelinks dictionary with title, and badges per site.

        Example:
            >>> import mwclient
            >>> site = mwclient.WikiBaseSite(('https', 'www.wikidata.org'))
            >>> q = mwclient.entity.Item(site, 'Q3340172')
            >>> q.sitelinks
        """
        if self._sitelinks is None:
            entities = self.site.api('wbgetentities', ids=self.entity)
            result = entities['entities'][self.entity]
            self.setinfofromwbgetentities(result)
        return self._sitelinks

    def __repr__(self):
        """Item representation."""
        return "<Item object %s (%s)>" % (self.entity, self.site.host)


class Property(Entity):

    """Wikibase Property."""

    def __init__(self, site, entity):
        """Constructor.

        Args:
            site (WikiBaseSite): reference to a WikiBaseSite
            entity (str): Q number of the entity.
        """
        # Normalizing entity name
        super(Property, self).__init__(site, 'P' + entity.upper().lstrip('P'))

    def __repr__(self):
        """Property representation."""
        return "<Property object %s (%s)>" % (self.entity, self.site.host)


class Claim(object):

    """Claim

    Attributes:
        prop (str): property id.
        snak (dict): snak with all values return in mainsnak from API call.
        snaktype (str): 'value', 'somevalue' or 'novalue'
        datatype (str): datatype ('wikibase-item', 'string', etc.)
        raw_value (dict): content of snak['datavalue']['value'] if snaktype is
            'value', None othewise.
        value (object): typed content of snak['datavalue']['value']
    """

    def __init__(self, site, prop, datatype, snaktype, raw_value=None, snak=None):
        """Constructor"""
        self.site = site
        self.prop = prop
        self.datatype = datatype
        self.raw_value = raw_value
        self.snaktype = snaktype
        self.snak = snak

    @classmethod
    def fromsnak(cls, site, snak):
        """Claim from snak dictionary.

        Args:
            site (mwclient.WikiBaseSite): site
            snak (dict): snak dictionary
        """
        snakvalue = None
        if snak['snaktype'] == 'value':
            snakvalue = snak['datavalue']['value']
        return cls(site, snak['property'],
                   snak['datatype'],
                   snak['snaktype'],
                   raw_value=snakvalue,
                   snak=snak)

    def __repr__(self):
        """Representation."""
        return "<Claim object %s [%s]>" % (self.prop, self.datatype)


    @property
    def value(self):
        if self.datatype == 'string':
            return self.raw_value
        elif self.datatype == 'monolingualtext':
            return MonolingualText(**self.raw_value)
        elif self.datatype == 'commonsMedia':
            return self.raw_value
        elif self.datatype == 'external-id':
            return self.raw_value
        elif self.datatype == 'wikibase-item':
            return Item(self.site, str(self.raw_value['numeric-id']))
        elif self.datatype == 'wikibase-property':
            return Property(self.site, str(self.raw_value['numeric-id']))
        elif self.datatype == 'globe-coordinate':
            return GlobeCoordinate(**self.raw_value)
        elif self.datatype == 'time':
            return TimeData(**self.raw_value)
        elif self.datatype == 'quantity':
            return Quantity(**self.raw_value)
        else:
            return self.raw_value


class GlobeCoordinate(object):
    def __init__(self, latitude=None, longitude=None, altitude=None, precision=None,
                 globe=None):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.precision = precision
        self.globe = globe

    def __repr__(self):
        return "<GlobeCoordinate {}... {}... {}... ...>".format(
            self.latitude,
            self.longitude,
            self.altitude)


class TimeData(object):
    def __init__(self, time=None, timezone=None, before=None, after=None, precision=None,
                 calendarmodel=None):
        self.time = time
        self.timezone = timezone
        self.before = before
        self.after = after
        self.precision = precision
        self.calendarmodel = calendarmodel


class Quantity(object):
    def __init__(self, amount=None, unit=None, upperBound=None, lowerBound=None):
        self.amount = amount
        self.unit = unit
        self.upperBound = upperBound
        self.lowerBound = lowerBound


class MonolingualText(object):
    def __init__(self, text=None, language=None):
        self.text = text
        self.language = language

    def __repr__(self):
        return "<MonolingualText [%s] '%s'>" % (self.language, self.text)
