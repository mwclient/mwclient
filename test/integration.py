import http.client
import logging
import shutil
import subprocess
import time
from typing import Optional
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

import pytest

import mwclient

if shutil.which("podman"):
    _CONTAINER_RUNTIME = "podman"
elif shutil.which("docker"):
    _CONTAINER_RUNTIME = "docker"
else:
    raise RuntimeError("Neither podman nor docker is installed")

@pytest.fixture(
    scope="class",
    params=[("latest", "5002"), ("legacy", "5003"), ("lts", "5004")],
    ids=["latest", "legacy", "lts"]
)
def site(request):
    """
    Run a mediawiki container for the duration of the class, yield
    a Site instance for it, then clean it up on exit. This is
    parametrized so we get three containers and run the tests three
    times for three mediawiki releases. We use podman because it's
    much easier to use rootless than docker.
    """
    (tag, port) = request.param
    container = f"mwclient-{tag}"
    # create the container, using upstream's official image. see
    # https://hub.docker.com/_/mediawiki
    args = [_CONTAINER_RUNTIME, "run", "--name", container, "-p", f"{port}:80",
            "-d", f"docker.io/library/mediawiki:{tag}"]
    subprocess.run(args)
    # configure the wiki far enough that we can use the API. if you
    # use this interactively the CSS doesn't work, I don't know why,
    # don't think it really matters
    args = [_CONTAINER_RUNTIME, "exec", container, "runuser", "-u", "www-data", "--",
            "php", "/var/www/html/maintenance/install.php", "--server",
            f"http://localhost:{port}", "--dbtype", "sqlite", "--pass", "weakpassword",
            "--dbpath", "/var/www/data", "mwclient-test-wiki", "root"]
    subprocess.run(args)
    # create a regular user
    args = [_CONTAINER_RUNTIME, "exec", container, "runuser", "-u", "www-data", "--",
            "php", "/var/www/html/maintenance/createAndPromote.php", "testuser",
            "weakpassword"]
    subprocess.run(args)
    # create an admin user
    args = [_CONTAINER_RUNTIME, "exec", container, "runuser", "-u", "www-data", "--",
            "php", "/var/www/html/maintenance/createAndPromote.php", "sysop",
            "weakpassword", "--bureaucrat", "--sysop", "--interface-admin"]
    subprocess.run(args)
    # create a bot user
    args = [_CONTAINER_RUNTIME, "exec", container, "runuser", "-u", "www-data", "--",
            "php", "/var/www/html/maintenance/createAndPromote.php", "testbot",
            "weakpassword", "--bot"]
    subprocess.run(args)
    # disable anonymous editing (we can't use redirection via podman
    # exec for some reason, so we use sed)
    args = [_CONTAINER_RUNTIME, "exec", container, "runuser", "-u", "www-data", "--",
            "sed", "-i", r"$ a\$wgGroupPermissions['*']['edit'] = false;",
            "/var/www/html/LocalSettings.php"]
    subprocess.run(args)
    # allow editing by users
    args = [_CONTAINER_RUNTIME, "exec", container, "runuser", "-u", "www-data", "--",
            "sed", "-i", r"$ a\$wgGroupPermissions['user']['edit'] = true;",
            "/var/www/html/LocalSettings.php"]
    subprocess.run(args)
    # allow file uploads
    args = [_CONTAINER_RUNTIME, "exec", container, "runuser", "-u", "www-data", "--",
        "sed", "-i", r"s/\$wgEnableUploads = false;/\$wgEnableUploads = true;/",
        "/var/www/html/LocalSettings.php"]
    subprocess.run(args)
    # block until the server is actually running, up to 30 seconds
    start = int(time.time())
    resp: Optional[http.client.HTTPResponse] = None
    while not resp:
        try:
            resp = urlopen(f"http://localhost:{port}")
        except (ValueError, URLError, HTTPError) as err:
            if int(time.time()) - start > 30:
                print("Waited more than 30 seconds for server to start!")
                raise err
            else:
                time.sleep(0.1)
    # set up mwclient.site instance and yield it
    yield mwclient.Site(f"localhost:{port}", path="/", scheme="http", force_login=False)
    # -t=0 just hard stops it immediately, saves time
    args = [_CONTAINER_RUNTIME, "stop", "-t=0", container]
    subprocess.run(args)
    args = [_CONTAINER_RUNTIME, "rm", container]
    subprocess.run(args)


class TestAnonymous:
    def test_page_load(self, site):
        """Test we can read a page from the sites."""
        pg = site.pages["Main_Page"]
        text = pg.text()
        assert text.startswith("<strong>MediaWiki has been installed")

    def test_page_create(self, site):
        """Test we get expected error if we try to create a page."""
        pg = site.pages["Anonymous New Page"]
        with pytest.raises(mwclient.errors.ProtectedPageError):
            pg.edit("Hi I'm a new page", "create new page")

    def test_expandtemplates(self, site):
        """Test we can expand templates."""
        wikitext = site.expandtemplates("{{CURRENTYEAR}}")
        assert wikitext == str(time.localtime().tm_year)

    def test_expandtemplates_with_parsetree(self, site):
        """Test we can expand templates and get the parse tree."""
        wikitext, parsetree = site.expandtemplates("{{CURRENTYEAR}}", generatexml=True)
        assert wikitext == str(time.localtime().tm_year)
        assert parsetree == "<root><template><title>CURRENTYEAR</title></template></root>"

class TestLogin:
    def test_login_wrong_password(self, site):
        """Test we raise correct error for login() with wrong password."""
        assert not site.logged_in
        with pytest.raises(mwclient.errors.LoginError):
            site.login(username="testuser", password="thisiswrong")
        assert not site.logged_in

    def test_login(self, site):
        """
        Test we can log in to the sites with login() and do authed
        stuff.
        """
        site.login(username="testuser", password="weakpassword")
        assert site.logged_in
        # test we can create a page
        pg = site.pages["Authed New Page"]
        pg.edit("Hi I'm a new page", "create new page")
        # we have to reinit because of Page.exists
        # https://github.com/mwclient/mwclient/issues/354
        pg = site.pages["Authed New Page"]
        assert pg.text() == "Hi I'm a new page"
        # test we can move it
        ret = pg.move("Authed Moved Page")
        pg = site.pages["Authed Moved Page"]
        assert pg.text() == "Hi I'm a new page"

    def test_page_delete(self, site):
        """Test we can login, create and delete a page as sysop."""
        site.login(username="sysop", password="weakpassword")
        pg = site.pages["Sysop New Page"]
        pg.edit("Hi I'm a new page", "create new page")
        pg = site.pages["Sysop New Page"]
        assert pg.text() == "Hi I'm a new page"
        assert pg.exists == True
        pg.delete()
        pg = site.pages["Sysop New Page"]
        assert pg.text() == ""
        assert pg.exists == False


class TestClient:
    def test_clientlogin_wrong_password(self, site):
        """Test we raise correct error for clientlogin() with wrong password."""
        with pytest.raises(mwclient.errors.LoginError):
            site.clientlogin(username="testuser", password="thisiswrong")
        assert not site.logged_in

    def test_clientlogin(self, site):
        """
        Test we can log in to the site with clientlogin() and
        create a page.
        """
        site.clientlogin(username="testuser", password="weakpassword")
        assert site.logged_in
        pg = site.pages["Anonymous New Page"]
        pg.edit("Hi I'm a new page", "create new page")
        pg = site.pages["Anonymous New Page"]
        assert pg.text() == "Hi I'm a new page"

    def test_site_revisions(self, site, caplog):
        caplog.set_level(logging.WARNING)
        # as per docstring example, make sure we don't crash for lack
        # of timestamp here
        rev = site.revisions([1], prop="content")[0]
        assert rev["pagetitle"] == "Main Page"
        # without limiting response
        rev = site.revisions([1])[0]
        assert rev["pagetitle"] == "Main Page"
        # check timestamp parsing
        assert isinstance(rev["timestamp"], time.struct_time)
        assert not caplog.text


class TestUploadAsync:
    def test_upload_async(self, site):
        filename = "test.jpg"

        site.login(username="testuser", password="weakpassword")
        assert site.logged_in

        with open("test/resources/cat.jpg", "rb") as f:
            stash_response = site.upload(
                file=f,
                filename=filename,
                description="Test image upload",
                stash=True,
            )

        filekey = stash_response["filekey"]
        assert filekey

        assert not site.Images[filename].exists

        site.upload(
            filekey=filekey,
            filename=filename,
            asynchronous=True,
        )

        assert site.Images[filename].exists
